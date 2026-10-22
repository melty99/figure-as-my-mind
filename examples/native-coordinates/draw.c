/* Synthetic software example: actual C CSV input and SVG + native geometry. */
#include "fam_bridge.h"
#include <stdlib.h>
int main(void) {
 double x[100],y[100],se[100],z[100];char ids_buf[100][40],line[256];const char *ids[100];size_t n=0,i;
 FILE *in=fopen("observations.csv","rb"),*out;fam_writer w;
 fam_axis ax={"Time","linear",0,7,1},ay={"Response","linear",0,8,1},az={"Z","linear",0,40,1};
 if(!in)return 1;fgets(line,sizeof(line),in);
 while(n<100&&fgets(line,sizeof(line),in)){if(sscanf(line,"%39[^,],%lf,%lf,%lf",ids_buf[n],&x[n],&y[n],&se[n])!=4){fclose(in);return 2;}ids[n]=ids_buf[n];z[n]=x[n]*x[n];n++;}fclose(in);
 out=fopen("c.scene.json","wb");if(!fam_native_begin(&w,out,6.4,4.8))return 3;
 fam_native_panel(&w,"points","C source result",&ax,&ay,NULL);fam_native_errorbar(&w,"Observed",x,y,se,se,n,"#4477aa",ids);
 fam_native_panel(&w,"xyz","Native XYZ",&ax,&ay,&az);fam_native_xyz(&w,"scatter","Observed XYZ",x,y,z,n,"#cc6677",ids);
 if(!fam_native_end(&w)){fclose(out);return 4;}fclose(out);
 out=fopen("c-original.svg","wb");if(!out)return 5;
 fputs("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"460\" height=\"340\"><text x=\"60\" y=\"30\" font-size=\"18\">C source result</text><path d=\"M60 50V290H430\" fill=\"none\" stroke=\"black\"/>",out);
 for(i=0;i<n;i++){double px=60+x[i]*50,py=290-y[i]*28;fprintf(out,"<path d=\"M%.8g %.8gV%.8g\" stroke=\"#222222\"/><circle cx=\"%.8g\" cy=\"%.8g\" r=\"4\" fill=\"#4477aa\"/>",px,py-se[i]*28,py+se[i]*28,px,py);}fputs("</svg>",out);fclose(out);
 out=fopen("c-import.json","wb");if(!out)return 6;fputs("{\"version\":1,\"language\":\"c\",\"source\":\"draw.c\",\"inputs\":[\"observations.csv\",\"fam_bridge.h\"],\"figures\":[{\"scene\":\"c.scene.json\",\"svg\":\"c-original.svg\",\"name\":\"C native coordinates\"}]}",out);fclose(out);return 0;
}
