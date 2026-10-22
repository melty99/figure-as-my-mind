# Explicit row IDs, not pixel proximity or incidental render order.
# Supported identity layers: point, col/bar, tile, segment and errorbar.
fam_save_semantic <- function(plot, file, rows, id_column, layers, x_column=NULL,
                              y_column=NULL, group_column=NULL, width=7.2, height=5.4) {
  for (pkg in c("ggplot2","svglite","xml2","jsonlite"))
    if (!requireNamespace(pkg,quietly=TRUE)) stop(paste("Missing package",pkg))
  if (!inherits(plot,"ggplot") || !id_column %in% names(rows)) stop("Declare a ggplot and source row ID column")
  ids <- as.character(rows[[id_column]])
  if (anyNA(ids) || any(!nzchar(ids)) || anyDuplicated(ids)) stop("Source row IDs must be complete and unique")
  if (!length(layers) || nrow(rows)>50000) stop("Declare layers; interactive adapter supports up to 50000 rows")
  original <- ggplot2::ggplot_build(plot)
  if (!inherits(original$layout$coord,"CoordCartesian")) stop("Semantic adapter requires Cartesian panels; polar coordinates need an explicit adapter")
  linked <- plot; specs <- list(); bound <- logical(nrow(rows))
  for (s in layers) {
    index <- as.integer(s$layer)
    if (length(index)!=1L || is.na(index) || index<1L || index>length(plot$layers)) stop("Invalid declared layer")
    layer <- plot$layers[[index]]
    if (!inherits(layer$stat,"StatIdentity") || !any(vapply(c("GeomPoint","GeomCol","GeomBar","GeomTile","GeomSegment","GeomErrorbar"),function(x) inherits(layer$geom,x),logical(1))))
      stop("Use explicit identity observations, not computed stat rows; provide a prepared result table for aggregate plots")
    data <- layer$data
    if (is.null(data) || inherits(data,"waiver")) data <- plot$data
    if (!is.data.frame(data) || !id_column %in% names(data)) stop("Every declared layer must contain the explicit source ID column")
    row_index <- match(as.character(data[[id_column]]),ids)
    if (anyNA(row_index) || anyDuplicated(row_index)) stop("Layer IDs must uniquely reference declared source rows")
    data$.fam_row_index <- row_index
    clone <- local({parent <- layer; ggplot2::ggproto(NULL,parent)})
    clone$data <- data; clone$mapping <- layer$mapping
    clone$mapping$fam_row_index <- ggplot2::aes(fam_row_index=.data$.fam_row_index)$fam_row_index
    linked$layers[[index]] <- clone
    specs[[as.character(index)]] <- list(role=if(is.null(s$role)) "data" else s$role)
    if (!specs[[as.character(index)]]$role %in% c("data","uncertainty")) stop("Role must be data or uncertainty")
  }
  built <- suppressWarnings(ggplot2::ggplot_build(linked))
  probe <- linked; row_lookup <- list()
  indices <- as.integer(names(specs))
  colours <- sprintf("#%06X",seq_len(nrow(rows)*length(indices))+65536L)
  if(length(colours)>16000000L) stop("Too many layer-row bindings")
  for (index in as.integer(names(specs))) {
    a <- original$data[[index]]; b <- built$data[[index]]
    keys <- intersect(c("x","y","xmin","xmax","ymin","ymax","xend","yend","PANEL","group","shape"),names(a))
    if (nrow(a)!=nrow(b) || !isTRUE(all.equal(a[keys],b[keys],check.attributes=FALSE))) stop("Row binding changed the original geometry or grouping")
    if (!"fam_row_index" %in% names(b) || anyNA(b$fam_row_index) || anyDuplicated(b$fam_row_index)) stop("Layer did not preserve unique declared IDs")
    row_lookup[[as.character(index)]] <- match(seq_len(nrow(rows)),b$fam_row_index)
    oldgeom <- linked$layers[[index]]$geom
    draw <- local({geom <- oldgeom; slot <- match(index,indices); palette <- colours[(slot-1L)*nrow(rows)+seq_len(nrow(rows))]
      function(data,panel_params,coord,...) {
        data$colour <- palette[as.integer(data$fam_row_index)]
        data$fill <- palette[as.integer(data$fam_row_index)]
        geom$draw_panel(data,panel_params,coord,...)
      }
    })
    probe$layers[[index]] <- local({parent <- linked$layers[[index]]; geom_parent <- oldgeom; drawer <- draw
      ggplot2::ggproto(NULL,parent,geom=ggplot2::ggproto(NULL,geom_parent,draw_panel=drawer))
    })
  }
  # Two independent SVG renders must have identical geometry and element order.
  # Only the probe's drawing colour changes; scales and legend remain original.
  probe_file <- tempfile(fileext=".svg"); output_file <- tempfile(fileext=".svg")
  on.exit(unlink(c(probe_file,output_file)),add=TRUE)
  fam_save(linked,output_file,width=width,height=height)
  fam_save(probe,probe_file,width=width,height=height)
  doc <- xml2::read_xml(output_file); test <- xml2::read_xml(probe_file)
  nodes <- xml2::xml_find_all(doc,"//*"); probes <- xml2::xml_find_all(test,"//*")
  if (length(nodes)!=length(probes) || !identical(xml2::xml_name(nodes),xml2::xml_name(probes))) stop("Probe changed SVG structure; no file committed")
  geometry <- c("x","y","cx","cy","r","rx","ry","x1","x2","y1","y2","width","height","d","points","transform")
  for (attr in geometry) if (!identical(xml2::xml_attr(nodes,attr),xml2::xml_attr(probes,attr))) stop("Probe changed SVG geometry; no file committed")
  seen <- integer(nrow(rows)); panel_seen <- list(); primary <- integer(nrow(rows))
  for(index in indices)if(specs[[as.character(index)]]$role=='data'){
    declared_rows <- built$data[[index]]$fam_row_index
    primary[declared_rows[primary[declared_rows]==0L]] <- index
  }
  for (j in seq_along(nodes)) {
    style <- paste(xml2::xml_attr(probes[[j]],"style"),xml2::xml_attr(probes[[j]],"stroke"),xml2::xml_attr(probes[[j]],"fill"))
    original_style <- paste(xml2::xml_attr(nodes[[j]],"style"),xml2::xml_attr(nodes[[j]],"stroke"),xml2::xml_attr(nodes[[j]],"fill"))
    if(identical(style,original_style)) next
    tags <- regmatches(toupper(style),gregexpr("#[0-9A-F]{6}",toupper(style)))[[1]]
    code <- unique(na.omit(match(tags,colours)))
    if (!length(code)) next
    if (length(code)!=1L) stop("Ambiguous probe colour")
    ri <- (code-1L) %% nrow(rows)+1L; index <- indices[(code-1L) %/% nrow(rows)+1L]
    node <- nodes[[j]]; ancestors <- xml2::xml_find_all(node,"ancestor::*[@clip-path]")
    if (!length(ancestors)) stop("Bound geometry must belong to a clipped panel")
    clip <- sub("^url\\(#(.*)\\)$","\\1",xml2::xml_attr(ancestors[[length(ancestors)]],"clip-path"))
    rect <- xml2::xml_find_first(doc,paste0("//*[local-name()='clipPath' and @id='",clip,"']/*[local-name()='rect']"))
    box <- as.numeric(xml2::xml_attrs(rect)[c("x","y","width","height")])
    if (any(!is.finite(box))) stop("Bound panel must have a rectangular clip")
    # Use the row's built panel, then verify the clip is consistently assigned.
    b <- built$data[[index]]; k <- row_lookup[[as.character(index)]][ri]
    if(is.na(k)) stop("Ambiguous layer-row identity")
    s <- list(panel=as.integer(b$PANEL[k]),role=specs[[as.character(index)]]$role); b <- b[k,,drop=FALSE]
    known <- panel_seen[[as.character(s$panel)]]
    if (!is.null(known) && !isTRUE(all.equal(known,box))) stop("Panel clip does not match source facet")
    panel_seen[[as.character(s$panel)]] <- box
    xy <- built$layout$coord$transform(b,built$layout$panel_params[[s$panel]])
    anchor <- c(box[1]+xy$x[1]*box[3],box[2]+(1-xy$y[1])*box[4])
    if (any(!is.finite(anchor))) stop("Missing/nonfinite coordinates require explicit filtering before binding")
    eid <- paste0("r-observation-",ri); seen[ri] <- seen[ri]+1L
    xml2::xml_set_attr(node,"id",paste0("r-linked-",ri,"-",seen[ri]))
    xml2::xml_set_attr(node,"data-fam-layer",s$role)
    if(inherits(plot$layers[[index]]$geom,"GeomPoint")){
      xml2::xml_set_attr(node,"data-fam-glyph-kind","point")
      xml2::xml_set_attr(node,"data-fam-point-size",as.character(as.numeric(b$size[1])*72/25.4))
    }
    own <- s$role=="data" && index==primary[ri] && !bound[ri]
    if (own) bound[ri] <- TRUE
    xml2::xml_set_attr(node,if(own) "data-fam-entity" else "data-fam-follow",eid)
    if (own) {
      xml2::xml_set_attr(node,"data-fam-sample",ids[ri])
      xml2::xml_set_attr(node,"data-fam-base",jsonlite::toJSON(c(as.numeric(b$x[1]),as.numeric(b$y[1])),auto_unbox=TRUE))
      xml2::xml_set_attr(node,"data-fam-coordinate-space","ggplot-built")
      xml2::xml_set_attr(node,"data-fam-anchor",jsonlite::toJSON(anchor,auto_unbox=TRUE))
      xml2::xml_set_attr(node,"data-fam-row",jsonlite::toJSON(as.list(rows[ri,,drop=FALSE]),auto_unbox=TRUE,na="null"))
      if(!is.null(group_column)) xml2::xml_set_attr(node,"data-fam-series",as.character(rows[[group_column]][ri]))
    }
  }
  declared <- unique(unlist(lapply(as.integer(names(specs)),function(index) if(specs[[as.character(index)]]$role=="data") built$data[[index]]$fam_row_index else integer())))
  owners <- xml2::xml_attr(nodes,"data-fam-entity")
  if(!length(declared)||!all(paste0("r-observation-",declared) %in% owners)) stop("Not all declared observations were rendered and bound")
  xml2::write_xml(doc,file)
  invisible(normalizePath(file))
}

fam_save_linked <- function(plot,file,rows,id_column,x_column,y_column,point_layer,error_layer=NULL,
                            group_column=NULL,width=7.2,height=5.4) {
  layers <- list(list(layer=point_layer,role="data"))
  if (!is.null(error_layer)) layers <- c(layers,list(list(layer=error_layer,role="uncertainty")))
  fam_save_semantic(plot,file,rows,id_column,layers,x_column,y_column,group_column,width,height)
}
