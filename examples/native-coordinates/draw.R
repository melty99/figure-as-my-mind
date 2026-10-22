# Synthetic software example. Analysis values remain in this original R source.
if(.Platform$OS.type=="windows" && getRversion()>="4.2") invisible(Sys.setlocale("LC_CTYPE","English_United States.utf8"))
args <- commandArgs(trailingOnly=FALSE)
root <- dirname(normalizePath(sub("^--file=","",args[grepl("^--file=",args)][1])))
setwd(root)
helper <- file.path(root,"helpers")
if(!dir.exists(helper)) dir.create(helper)
for(n in c("bridge.R","bridge_semantic.R","ggplot_bridge.R","bridge_native.R")) if(!file.exists(file.path(helper,n))) file.copy(file.path(root,"..","..","scripts",n),helper)
source(file.path(helper,"bridge.R"),encoding="UTF-8")
d <- read.csv("observations.csv",stringsAsFactors=FALSE)
fam_save(function() { plot(d$x,d$y,pch=16,col="#4477aa",xlab="Time",ylab="Response",main="R source result"); segments(d$x,d$y-d$se,d$x,d$y+d$se) },"r-original.svg")
points <- fam_layer("errorbar",d$x,d$y,label="Observed",ids=d$id,rows=d,
 errors=list(y=d$se),style=list(color="#4477aa",errorColor="#222222",size=5,marker="o"))
values <- outer(seq(-1,1,length.out=5),seq(-1,1,length.out=6),function(a,b) a*a+b*b)
scene <- list(fam_panel(list(points),title="R source result",x=list(label="Time"),y=list(label="Response")),
 fam_panel(list(fam_layer("surface",x=seq(-1,1,length.out=6),y=seq(-1,1,length.out=5),values=values,colorbarTitle="Value")),id="surface",title="Computed grid",z=list(label="Value")))
fam_save_native(scene,"r.scene.json")
fam_manifest("draw.R",figures=list(list(scene="r.scene.json",svg="r-original.svg",name="R native coordinates")),inputs=c("observations.csv",paste0("helpers/",c("bridge.R","bridge_semantic.R","ggplot_bridge.R","bridge_native.R"))),datasets=list(list(path="observations.csv",name="Synthetic example")),file="r-import.json")
