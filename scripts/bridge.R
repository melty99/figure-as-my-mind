# SVG bridge for R. Source this file in the original plotting script.
# Uses base R grDevices; ggplot2 functions use ggplot2 if already installed.
fam_save <- function(plot, file, width=6.4, height=4.8, bg="transparent", semantic_text=TRUE) {
  if (isTRUE(semantic_text)) {
    if (!requireNamespace("svglite", quietly=TRUE)) stop("Editable text requires svglite; install it or explicitly set semantic_text=FALSE")
    svglite::svglite(file, width=width, height=height, bg=bg)
  } else grDevices::svg(file, width=width, height=height, onefile=TRUE, bg=bg)
  on.exit(grDevices::dev.off(), add=TRUE)
  if (is.function(plot)) plot() else print(plot)
  invisible(normalizePath(file))
}

fam_theme <- function(settings_file, figure_id=NULL) {
  if (!requireNamespace("jsonlite", quietly=TRUE)) stop("fam_theme requires jsonlite")
  if (!requireNamespace("ggplot2", quietly=TRUE)) stop("fam_theme requires ggplot2")
  config <- jsonlite::fromJSON(settings_file, simplifyVector=FALSE)
  f <- config$figures[[1]]
  if (!is.null(figure_id)) {
    found <- Filter(function(x) identical(x$id, figure_id), config$figures)
    if (length(found) != 1) stop("Figure id not found")
    f <- found[[1]]
  }
  s <- f$style
  ggplot2::theme(text=ggplot2::element_text(family=s$fontFamily, size=s$fontSize, colour=s$textColor),
    plot.title=ggplot2::element_text(size=s$titleSize),
    axis.title=ggplot2::element_text(size=s$labelSize),
    axis.text=ggplot2::element_text(size=s$tickSize),
    panel.border=if (isTRUE(s$spines)) ggplot2::element_rect(fill=NA, linewidth=s$lineWidth) else ggplot2::element_blank(),
    plot.background=ggplot2::element_rect(fill=if(isTRUE(s$transparent)) "transparent" else s$background, colour=NA),
    panel.grid=if (isTRUE(s$grid)) ggplot2::element_line(colour="#dddddd") else ggplot2::element_blank())
}
# Declare already generated figures and their source/data for import-vector.
# Does not execute code or infer statistical/point relationships from an image.
fam_manifest <- function(source, figures, inputs=character(), datasets=list(), file="import-manifest.json") {
  if(!requireNamespace("jsonlite",quietly=TRUE)) stop("fam_manifest requires jsonlite")
  config <- list(version=1L, language="r", source=source, inputs=as.list(inputs), figures=figures, datasets=datasets)
  jsonlite::write_json(config, file, auto_unbox=TRUE, pretty=TRUE, null="null")
  invisible(normalizePath(file))
}

# Companion adapter retains explicit IDs through build and checks SVG geometry.
.fam_bridge_path <- sys.frame(1)$ofile
if (is.null(.fam_bridge_path)) stop("Load bridge.R with source() so its semantic adapter can be located")
source(file.path(dirname(.fam_bridge_path), "bridge_semantic.R"), local=TRUE, encoding="UTF-8")
source(file.path(dirname(.fam_bridge_path), "ggplot_bridge.R"), local=TRUE, encoding="UTF-8")
if(file.exists(file.path(dirname(.fam_bridge_path), "bridge_native.R"))) source(file.path(dirname(.fam_bridge_path), "bridge_native.R"), local=TRUE, encoding="UTF-8")
rm(.fam_bridge_path)
