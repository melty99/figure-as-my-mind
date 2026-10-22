function draw_matlab
% Synthetic software example. Uses native MATLAB objects and explicit identities.
root=fileparts(mfilename('fullpath'));helper=fullfile(root,'helpers');
if ~exist(helper,'dir'),mkdir(helper);end
if ~exist(fullfile(helper,'fam_save_figure.m'),'file'),copyfile(fullfile(root,'..','..','scripts','fam_save_figure.m'),helper);end
addpath(helper);
d=readtable(fullfile(root,'observations.csv'));
f=figure('Visible','off','Color','none');a=subplot(1,2,1,'Parent',f);
h=errorbar(a,d.x,d.y,d.se,'o','Color',[.267 .467 .667],'DisplayName','Observed');
setappdata(h,'FAMSampleIDs',d.id);setappdata(h,'FAMSourceRows',d);
xlabel(a,'Time');ylabel(a,'Response');title(a,'MATLAB source result');legend(a,'show');
a=subplot(1,2,2,'Parent',f);scatter3(a,d.x,d.y,d.x.^2,35,d.x,'filled');
xlabel(a,'X');ylabel(a,'Y');zlabel(a,'Z');title(a,'Native XYZ');view(a,35,25);colorbar(a);
fam_save_figure(f,fullfile(root,'matlab.scene.json'));saveas(f,fullfile(root,'matlab-original.svg'));close(f);
manifest=struct('version',1,'language','matlab','source','draw_matlab.m','inputs',{{'observations.csv','helpers/fam_save_figure.m'}},...
 'figures',{{struct('scene','matlab.scene.json','svg','matlab-original.svg','name','MATLAB native coordinates')}});
file=fopen(fullfile(root,'matlab-import.json'),'w','n','UTF-8');fprintf(file,'%s',jsonencode(manifest));fclose(file);
end
