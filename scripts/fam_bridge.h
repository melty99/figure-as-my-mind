/* Figure as My Mind: explicit native coordinates, ISO C99, no plotting dependency.
   The caller computes its statistics, owns FILE*, and supplies UTF-8 strings.
   Native scene import is performed later; this header does not launch processes. */
#ifndef FAM_NATIVE_BRIDGE_H
#define FAM_NATIVE_BRIDGE_H
#include <stdio.h>
#include <stddef.h>
#include <string.h>
#include <math.h>
#include <locale.h>
typedef struct { const char *label,*scale; double lower,upper; int has_limits; } fam_axis;
typedef struct { FILE *file; size_t panels,layers; int panel_open,failed; } fam_writer;
static void fam_string(fam_writer *w,const char *s) {
 const unsigned char *p=(const unsigned char *)(s?s:"");fputc('"',w->file);
 while(*p){ unsigned char c=*p++;if(c=='"'||c=='\\'){fputc('\\',w->file);fputc(c,w->file);}
 else if(c<32)fprintf(w->file,"\\u%04x",(unsigned)c);else fputc(c,w->file); }
 fputc('"',w->file);
}
static void fam_number(fam_writer *w,double x) {
 char b[80],*mark;const char *decimal;
 if(!isfinite(x)){fputs("null",w->file);return;}
 snprintf(b,sizeof(b),"%.17g",x);decimal=localeconv()->decimal_point;
 mark=(decimal&&*decimal&&strcmp(decimal,"."))?strstr(b,decimal):NULL;
 if(mark){*mark=0;fputs(b,w->file);fputc('.',w->file);fputs(mark+strlen(decimal),w->file);}else fputs(b,w->file);
}
static void fam_array(fam_writer *w,const double *a,size_t n) {
 size_t i;fputc('[',w->file);for(i=0;i<n;i++){if(i)fputc(',',w->file);fam_number(w,a[i]);}fputc(']',w->file);
}
static void fam_axis_json(fam_writer *w,const fam_axis *a) {
 fputs("{\"label\":",w->file);fam_string(w,a?a->label:"");
 if(a&&a->scale){fputs(",\"scale\":",w->file);fam_string(w,a->scale);}
 if(a&&a->has_limits){fputs(",\"range\":[",w->file);fam_number(w,a->lower);fputc(',',w->file);fam_number(w,a->upper);fputc(']',w->file);}
 fputc('}',w->file);
}
static int fam_native_begin(fam_writer *w,FILE *file,double width,double height) {
 if(!w||!file||!isfinite(width)||!isfinite(height)||width<=0||height<=0)return 0;
 memset(w,0,sizeof(*w));w->file=file;fputs("{\"version\":1,\"kind\":\"fam-native\",\"width\":",file);fam_number(w,width);fputs(",\"height\":",file);fam_number(w,height);fputs(",\"panels\":[",file);return 1;
}
static void fam_native_panel(fam_writer *w,const char *id,const char *title,const fam_axis *x,const fam_axis *y,const fam_axis *z) {
 if(w->panel_open)fputs("]}",w->file);if(w->panels++)fputc(',',w->file);w->panel_open=1;w->layers=0;
 fputs("{\"id\":",w->file);fam_string(w,id);fputs(",\"title\":",w->file);fam_string(w,title);
 fputs(",\"x\":",w->file);fam_axis_json(w,x);fputs(",\"y\":",w->file);fam_axis_json(w,y);
 if(z){fputs(",\"projection\":\"3d\",\"z\":",w->file);fam_axis_json(w,z);}fputs(",\"layers\":[",w->file);
}
static int fam_layer_start(fam_writer *w,const char *kind,const char *label,const double *x,const double *y,const double *z,size_t n,const char *color,const char *const *ids) {
 size_t i;if(!w||!w->panel_open||!x||!y||!n){if(w)w->failed=1;return 0;}
 if(w->layers++)fputc(',',w->file);fputs("{\"kind\":",w->file);fam_string(w,kind);
 if(label&&*label){fputs(",\"label\":",w->file);fam_string(w,label);}
 fputs(",\"x\":",w->file);fam_array(w,x,n);fputs(",\"y\":",w->file);fam_array(w,y,n);
 if(z){fputs(",\"z\":",w->file);fam_array(w,z,n);}
 if(ids){fputs(",\"sourceIds\":[",w->file);for(i=0;i<n;i++){if(i)fputc(',',w->file);fam_string(w,ids[i]);}fputc(']',w->file);}
 fputs(",\"style\":{\"color\":",w->file);fam_string(w,color?color:"#4477aa");fputc('}',w->file);return 1;
}
static void fam_native_xy(fam_writer *w,const char *kind,const char *label,const double *x,const double *y,size_t n,const char *color,const char *const *ids) {
 if(strcmp(kind,"scatter")&&strcmp(kind,"line")&&strcmp(kind,"bar")){w->failed=1;return;}
 if(fam_layer_start(w,kind,label,x,y,NULL,n,color,ids))fputc('}',w->file);
}
static void fam_native_xyz(fam_writer *w,const char *kind,const char *label,const double *x,const double *y,const double *z,size_t n,const char *color,const char *const *ids) {
 if(!z||(strcmp(kind,"scatter")&&strcmp(kind,"line"))){w->failed=1;return;}
 if(fam_layer_start(w,kind,label,x,y,z,n,color,ids))fputc('}',w->file);
}
static void fam_native_errorbar(fam_writer *w,const char *label,const double *x,const double *y,const double *minus,const double *plus,size_t n,const char *color,const char *const *ids) {
 if(!minus||!plus){w->failed=1;return;}
 if(fam_layer_start(w,"errorbar",label,x,y,NULL,n,color,ids)) {
  fputs(",\"errors\":{\"y\":{\"minus\":",w->file);fam_array(w,minus,n);fputs(",\"plus\":",w->file);fam_array(w,plus,n);fputs("}}}",w->file);
 }
}
static int fam_native_end(fam_writer *w) {
 if(!w||!w->file)return 0;if(w->panel_open)fputs("]}",w->file);fputs("]}",w->file);return !w->failed&&!ferror(w->file)&&w->panels>0;
}
#endif
