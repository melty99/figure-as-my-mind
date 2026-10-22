# Explicit native coordinates from any R plotting workflow.
# Summaries/models are computed by the original R code before calling this bridge.
fam_layer <- function(kind, x=NULL, y=NULL, z=NULL, label=NULL, ids=NULL, rows=NULL,
                      errors=NULL, style=list(), ...) {
  allowed <- c("scatter","line","errorbar","bar","matrix","surface")
  if (!kind %in% allowed) stop("Unsupported native layer kind")
  if(!length(style)) style <- list(color="#4477aa")
  out <- list(kind=kind, style=style)
  array <- function(v) as.list(unname(v))
  for(n in c("x","y","z")) { v <- get(n); if(!is.null(v)) out[[n]] <- array(v) }
  if(!is.null(label)) out$label <- as.character(label)
  if(!is.null(ids)) { if(length(ids)!=length(x) || anyNA(ids) || anyDuplicated(ids)) stop("IDs must match observations and be unique"); out$sourceIds <- array(as.character(ids)) }
  if(!is.null(rows)) {
    if(!is.data.frame(rows) || nrow(rows)!=length(x)) stop("Source rows must match observations")
    out$rows <- lapply(seq_len(nrow(rows)),function(i) as.list(rows[i,,drop=FALSE]))
  }
  if(!is.null(errors)) out$errors <- lapply(errors,function(e) {
    if(is.numeric(e)) e <- list(minus=e,plus=e)
    list(minus=array(e$minus),plus=array(e$plus))
  })
  extra <- list(...)
  for(n in names(extra)) {
    v <- extra[[n]]
    if(n=="values") {
      if(!is.matrix(v)) stop("values must be a matrix")
      v <- lapply(seq_len(nrow(v)),function(i) array(v[i,]))
    } else if(n %in% c("colors","edgeColors","palette","colorValues","sizes","clim")) v <- array(v)
    out[[n]] <- v
  }
  out
}

fam_panel <- function(layers, id="panel-1", title="", x=list(), y=list(), z=NULL,
                      projection=if(is.null(z)) "2d" else "3d", annotations=list(), ...) {
  if(!is.list(layers) || !length(layers)) stop("At least one layer is required")
  axis <- function(a) { if(!length(a)) a <- list(label=""); for(k in c("range","ticks","tickLabels")) if(!is.null(a[[k]])) a[[k]] <- as.list(a[[k]]); a }
  out <- c(list(id=as.character(id),title=title,x=axis(x),y=axis(y),layers=layers,
                projection=projection,annotations=annotations),list(...))
  if(!is.null(z)) out$z <- axis(z)
  out
}

fam_save_native <- function(panels, file, width=6.4, height=4.8, fontFamily="Arial", fontSize=11, columns=2L) {
  if(!requireNamespace("jsonlite",quietly=TRUE)) stop("fam_save_native requires jsonlite")
  if(!is.list(panels) || !length(panels)) stop("Provide a list of independent panels")
  scene <- list(version=1L,kind="fam-native",width=width,height=height,fontFamily=fontFamily,
                fontSize=fontSize,columns=as.integer(columns),panels=panels)
  jsonlite::write_json(scene,file,auto_unbox=TRUE,pretty=FALSE,null="null",na="null",digits=NA)
  invisible(normalizePath(file))
}
