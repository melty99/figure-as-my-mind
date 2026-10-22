function scene = fam_save_figure(fig, sceneFile)
%FAM_SAVE_FIGURE Capture explicit MATLAB coordinates for Figure as My Mind.
% Does not run Python, change observations, fit models or overwrite the figure.
% Cartesian line/scatter/errorbar/bar/image/surface and data-coordinate text.
% Set FAMSampleIDs/FAMSourceRows appdata on a series for original-row identity.
if ~isgraphics(fig,'figure'), error('FAM:Figure','Provide a MATLAB figure'); end
axesList=findall(fig,'Type','axes');axesList=flipud(axesList(:));
if isempty(axesList), error('FAM:Axes','No supported Cartesian axes found'); end
scene=struct('version',1,'kind','fam-native','width',6.4,'height',4.8,...
 'fontFamily','Arial','fontSize',11,'columns',2,'panels',{{}});
for ai=1:numel(axesList)
 ax=axesList(ai);
 if numel(ax.YAxis)>1, error('FAM:DualAxes','Dual Y axes need an explicit dedicated adapter'); end
 if ~strcmp(ax.XScale,'linear') || ~strcmp(ax.YScale,'linear')
  if ~isequal(ax.View,[0 90]), error('FAM:Log3D','Logarithmic true-3D axes need a dedicated adapter'); end
 end
 scene.fontFamily=ax.FontName;scene.fontSize=ax.FontSize;
 p=struct('id',sprintf('panel-%d',ai),'title',stringText(ax.Title.String),...
  'x',axisInfo(ax,'X'),'y',axisInfo(ax,'Y'),'layers',{{}},'annotations',{{}},'legend',isprop(ax,'Legend') && ~isempty(ax.Legend));
 dataChildren=ax.Children;hasZ=false;
 for zi=1:numel(dataChildren),h0=dataChildren(zi);if isprop(h0,'ZData') && ~isempty(h0.ZData),hasZ=true;end;end
 is3d=~isequal(ax.View,[0 90]) || hasZ;
 if is3d && (~strcmp(ax.XScale,'linear') || ~strcmp(ax.YScale,'linear') || ~strcmp(ax.ZScale,'linear')),error('FAM:Log3D','Nonlinear true-3D coordinates need a dedicated adapter');end
 if is3d
  p.projection='3d';p.z=axisInfo(ax,'Z');
  p.camera=struct('azimuth',ax.View(1),'elevation',ax.View(2),'projection',projectionName(ax.Projection));
 else,p.projection='2d';end
 children=flipud(ax.Children(:));barCount=sum(arrayfun(@(h) strcmp(h.Type,'bar'),children));
 for j=1:numel(children)
  h=children(j);if strcmp(h.Visible,'off'),continue;end
  typ=h.Type;
  if strcmp(typ,'text')
   if any(h==[ax.Title ax.XLabel ax.YLabel ax.ZLabel]),continue;end
   if ~strcmp(h.Units,'data'),error('FAM:TextUnits','Only explicit data-coordinate annotations are supported');end
   note=struct('x',h.Position(1),'y',h.Position(2),'text',stringText(h.String),...
    'fontSize',h.FontSize,'fontFamily',h.FontName,'color',h.Color,'rotation',h.Rotation);
   if is3d,note.z=h.Position(3);end
   p.annotations{end+1}=note;continue
  end
  if ~ismember(typ,{'line','scatter','errorbar','bar','image','surface'})
   error('FAM:Unsupported','Unsupported graphics type %s. Use source-specific adaptation; no screenshot fallback.',typ);
  end
  st=struct('color',[.267 .467 .667],'alpha',1,'lineWidth',1,'marker','o','size',5);
  if isprop(h,'Color'),st.color=h.Color;end
  if isprop(h,'LineWidth'),st.lineWidth=h.LineWidth;end
  if isprop(h,'LineStyle'),st.lineStyle=h.LineStyle;end
  if isprop(h,'Marker'),st.marker=markerName(h.Marker);end
  if isprop(h,'MarkerSize'),st.size=h.MarkerSize;end
  if isprop(h,'MarkerFaceColor') && (isnumeric(h.MarkerFaceColor)||strcmpValue(h.MarkerFaceColor,'none')),st.faceColor=h.MarkerFaceColor;end
  if isprop(h,'MarkerEdgeColor') && ~strcmpValue(h.MarkerEdgeColor,'auto') && ~strcmpValue(h.MarkerEdgeColor,'flat'),st.edgeColor=h.MarkerEdgeColor;end
  if strcmp(typ,'surface') && (isnumeric(h.EdgeColor)||strcmpValue(h.EdgeColor,'none')),st.edgeColor=h.EdgeColor;end
  layer=struct('kind',typ,'style',st);
  if isprop(h,'DisplayName') && ~isempty(h.DisplayName),layer.label=h.DisplayName;end
  if strcmp(typ,'image') || strcmp(typ,'surface')
   if strcmp(typ,'image')
    if ~strcmp(h.CDataMapping,'scaled'),error('FAM:ImageMapping','Direct indexed images need a dedicated numeric mapping adapter');end
    if ndims(h.CData)~=2,error('FAM:RGBImage','RGB images remain raster references; declare a numeric matrix for editable mapping');end
    layer.kind='matrix';layer.values=asMatrix(h.CData);[nr,nc]=size(h.CData);
    layer.x=asArray(linspace(h.XData(1),h.XData(end),nc));layer.y=asArray(linspace(h.YData(1),h.YData(end),nr));
   else
    if ~isequaln(h.CData,h.ZData),error('FAM:SurfaceColor','Surface colors independent of Z need an explicit color-data adapter');end
    layer.values=asMatrix(h.ZData);xx=h.XData;yy=h.YData;
    if ~ismatrix(xx) || ~ismatrix(yy) || ~isequal(size(xx),size(h.ZData)) || ~isequal(size(yy),size(h.ZData)),error('FAM:Surface','Only explicit rectilinear grid surfaces are supported');end
    if any(any(abs(xx-repmat(xx(1,:),size(xx,1),1))>1e-10)) || any(any(abs(yy-repmat(yy(:,1),1,size(yy,2)))>1e-10)),error('FAM:Surface','Curvilinear surfaces need their own geometry adapter');end
    layer.x=asArray(xx(1,:));layer.y=asArray(yy(:,1));p.projection='3d';p.z=axisInfo(ax,'Z');
    p.camera=struct('azimuth',ax.View(1),'elevation',ax.View(2),'projection',projectionName(ax.Projection));
   end
   layer.palette=num2cell(colormap(ax),2);layer.clim=asArray(ax.CLim);
   layer.colorbar=hasColorbar(ax);
  else
   if ~isnumeric(h.XData)||~isnumeric(h.YData),error('FAM:Coordinates','Datetime/categorical data need explicit numeric coordinates and tick labels');end
   layer.x=asArray(h.XData);layer.y=asArray(h.YData);n=numel(h.XData);
   if strcmp(typ,'line'),layer.kind='line';end
   if is3d && isprop(h,'ZData'),layer.z=asArray(h.ZData);end
   if strcmp(typ,'scatter')
    layer.sizes=asArray(sqrt(h.SizeData));if numel(h.SizeData)==1,layer.sizes=repmat(layer.sizes,1,n);end
    cd=h.CData;
    if size(cd,2)==3 && size(cd,1)>1,layer.colors=num2cell(cd,2);
    elseif size(cd,1)==1 && size(cd,2)==3,layer.style.color=reshape(cd,1,3);
    else
     if isscalar(cd),cd=repmat(cd,n,1);end
     layer.colorValues=asArray(cd);layer.palette=num2cell(colormap(ax),2);layer.clim=asArray(ax.CLim);layer.colorbar=hasColorbar(ax);
    end
    if strcmpValue(h.MarkerEdgeColor,'flat')
     if isfield(layer,'colors'),layer.edgeColors=layer.colors;
     elseif isfield(layer,'colorValues')
      palette=colormap(ax);cv=reshape(double(cd),[],1);ix=floor((cv-ax.CLim(1))/diff(ax.CLim)*size(palette,1))+1;ix=max(1,min(size(palette,1),ix));ix(~isfinite(ix))=1;layer.edgeColors=num2cell(palette(ix,:),2);
     end
    elseif strcmpValue(h.MarkerEdgeColor,'none'),layer.style.edgeColor='none';end
    if isnumeric(h.MarkerFaceAlpha),layer.style.alpha=h.MarkerFaceAlpha;end
   end
   if strcmp(typ,'errorbar')
    layer.errors=struct();
    for d={'X','Y'}
     dim=d{1};minus=h.([dim 'NegativeDelta']);plus=h.([dim 'PositiveDelta']);
     if ~isempty(minus) || ~isempty(plus)
      if isempty(minus),minus=zeros(size(plus));end;if isempty(plus),plus=zeros(size(minus));end
      layer.errors.(lower(dim))=struct('minus',{asArray(minus)},'plus',{asArray(plus)});
     end
    end
   end
   if strcmp(typ,'bar')
    layer.horizontal=strcmp(h.Horizontal,'on');base=h.BaseValue;data=h.YData;
    if layer.horizontal,center=h.YEndPoints;top=h.XEndPoints;else,center=h.XEndPoints;top=h.YEndPoints;end
    layer.x=asArray(center);layer.y=asArray(data);layer.bottom=asArray(top-data);
    xd=unique(double(h.XData));step=1;if numel(xd)>1,step=min(diff(xd));end
    layer.width=double(h.BarWidth)*step;
    if strcmp(h.BarLayout,'grouped') && barCount>1,layer.width=layer.width/barCount;end
    if isnumeric(h.FaceColor),layer.style.color=h.FaceColor;elseif strcmpValue(h.FaceColor,'flat') && size(h.CData,2)==3,layer.colors=num2cell(h.CData,2);end
    if isnumeric(h.EdgeColor)||strcmpValue(h.EdgeColor,'none'),layer.style.edgeColor=h.EdgeColor;end
    layer.style.alpha=h.FaceAlpha;layer.style.marker='none';layer.style.lineStyle='none';
   end
   if isappdata(h,'FAMSampleIDs')
    ids=getappdata(h,'FAMSampleIDs');ids=cellstr(string(ids));
    if numel(ids)~=n || numel(unique(ids))~=n,error('FAM:Identity','FAMSampleIDs must uniquely match series observations');end
    layer.sourceIds=reshape(ids,1,[]);
   end
   if isappdata(h,'FAMSourceRows')
    rows=getappdata(h,'FAMSourceRows');if istable(rows),rows=table2struct(rows);end
    if numel(rows)~=n,error('FAM:Rows','FAMSourceRows must match observations');end
    layer.rows=reshape(arrayfun(@(r) r,rows,'UniformOutput',false),1,[]);
   end
  end
  p.layers{end+1}=layer;
 end
 if isempty(p.layers),error('FAM:Empty','The selected axes have no supported data layers');end
 scene.panels{end+1}=p;
end
file=fopen(sceneFile,'w','n','UTF-8');if file<0,error('FAM:Output','Cannot write scene');end
cleanup=onCleanup(@()fclose(file));fwrite(file,unicode2native(jsonencode(scene),'UTF-8'),'uint8');
end
function yes=hasColorbar(ax)
yes=isprop(ax,'Colorbar') && ~isempty(ax.Colorbar) && isgraphics(ax.Colorbar) && strcmp(ax.Colorbar.Visible,'on');
end
function a=axisInfo(ax,dim)
limits=ax.([dim 'Lim']);if strcmp(ax.([dim 'Dir']),'reverse'),limits=fliplr(limits);end
labels=cellstr(string(ax.([dim 'TickLabel'])));ticks=ax.([dim 'Tick']);
a=struct('label',stringText(ax.([dim 'Label']).String),'range',{asArray(limits)},'scale',ax.([dim 'Scale']),'ticks',{asArray(ticks)});
if numel(labels)==numel(ticks),a.tickLabels=reshape(labels,1,[]);end
end
function m=markerName(x)
switch x
 case 'square',m='s';case 'diamond',m='D';case 'pentagram',m='p';case 'hexagram',m='h';otherwise,m=x;
end
end
function m=asMatrix(x)
m=cell(size(x,1),1);for i=1:size(x,1),m{i}=asArray(x(i,:));end
end
function p=projectionName(x)
if strcmp(x,'orthographic'),p='ortho';else,p='persp';end
end
function v=asArray(x)
v=num2cell(reshape(double(x),1,[]));
end
function text=stringText(x)
if iscell(x)||isstring(x),text=strjoin(cellstr(string(x)),newline);else,text=char(x);end
end
function same=strcmpValue(x,y)
same=(ischar(x)||isstring(x))&&strcmp(x,y);
end
