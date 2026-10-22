# Figure as My Mind: From Plotting Code to Visual Editing

[简体中文](introduction.md) · **English**

[README](README.md) · [Installation](skills/figure-as-my-mind/docs/安装与启动.md) · [Full tutorial](skills/figure-as-my-mind/docs/教程.md)

Preparing a scientific figure often means repeatedly adjusting the plotting area, titles, legends, font sizes and panel layout. Figure as My Mind keeps the source code and data, brings these edits into a local browser workbench, and lets you take the final settings back to code.

The seven GIFs below show actual workbench operations. Complete the [quick start](README.md#快速开始), then try the [synthetic CSV examples](examples/quickstart/README.md) before using the same workflow with your own code. Editing capabilities differ between plain SVGs and figures with native semantic information; see the notes at the end. The linked README and detailed reference documents are currently in Chinese.

Switch the workbench to **English** using the language button at the top. The GIFs below show the English interface.

## 1. Resize the plotting area

**Goal: change the width and height of the plotting area while preserving the meaning of the data.**

![Widening, flattening, narrowing and stretching the plotting area](docs/media/en/01-axes-resize.gif)

1. Select a figure in the left panel. For a composition, first open the panel you want to edit.
2. Switch to the “Plot frame” layer and select the plotting area.
3. Drag an edge or corner handle. The left and right edges change the width; the top and bottom edges change the height. You can also enter dimensions in the right sidebar.
4. Check that data marks, error bars and ticks are remapped with the axes. This changes the dimensions, not the observed values.

The GIF deliberately shows large changes. Linked panels share the **actual width and height of their axes frames**, rather than forcing the entire image containers to the same size. Maps with a fixed aspect ratio, polar plots and 3D figures follow their applicable layout rules; stretching a map is not a substitute for changing its projection.

For more editing space, drag the inner edge of either sidebar. Preview zoom changes only the on-screen display, not the output dimensions.

## 2. Set axis limits and major ticks

**Goal: choose the visible range and which values appear on the axis.**

![Editing axis limits](docs/media/en/02-axis-range.gif)

1. Right-click an axis in a figure with native coordinate information to open the axis-range sidebar.
2. Choose X or Y, enter the lower and upper limits, and watch the preview.
3. Use the **major tick locator** to specify an interval, a count or custom positions.
4. Check the linked elements, then apply the change. Undo if needed.

For an axis ranging from 0 to 10:

| Desired ticks | Setting |
| --- | --- |
| 0, 5, 10 | A major tick interval of 5, or custom positions |
| 0, 2, 4, 6, 8, 10 | A major tick interval of 2, or six major ticks including both endpoints |
| Specific values at unequal intervals | Custom major tick positions |

The same sidebar offers linear, ln, log₂ and log₁₀ scales. Logarithmic scales require positive data and limits; changing the display scale does not rewrite the original input. On categorical axes, you can edit label styling and rotation without treating categories as continuous numerical values.

## 3. Move and resize legends

**Goal: make the legend readable without covering the data.**

![Moving and resizing a complete legend](docs/media/en/03-legend-edit.gif)

1. Switch to the legend/colorbar layer, select the whole legend and drag it into position.
2. Drag its bounding-box handles to scale it proportionally. Symbols, text and the border change together.
3. Double-click the legend to edit its orientation, rows and columns, entry order, and spacing between symbols and text in the fixed right sidebar.
4. When changing a categorical color, choose the relevant series and scope, then check that the corresponding data series updates.

For continuous colorbars, the editor exposes applicable controls such as gradient stops, colors, dimensions and ticks. The internal legend layout and the position of the complete legend can be edited separately. To change only an error bar’s color, use the error layer; its positional link to the associated data mark remains intact.

## 4. Refine panel typography and colorbars

**Goal: share common formatting while preserving each panel’s own content.**

![Linked font-size edits and an independently edited colorbar in another panel](docs/media/en/04-panel-style.gif)

1. Check at least two figures in the left panel and create a composition. Follow the workflow to edit individual panels before viewing the complete composition.
2. Keep linked edits for the current composition enabled when changing compatible shared formatting. In the GIF, the font sizes in both panels update together.
3. Select another panel from the panel list and adjust its continuous color scale, colorbar tick font size and dimensions independently.
4. Enable the linked-edit lock on panels that need independent formatting before updating the others.

Double-click text to edit applicable properties, including font family, size, bold, italic, rotation angle, color and alignment. The fixed right sidebar keeps the figure visible as you work. Tick-label edits can apply to an entire axis; axis titles and tick labels are edited separately.

Use “Move panels” to move a panel container. Return to element editing when working on axes, points or legends. The linked-edit lock and the layout/movement lock serve different purposes: locking a canvas does not lock formatting synchronization.

## 5. Rotate 3D panels together

**Goal: change the camera angles together when comparing two 3D panels.**

![Real-time synchronized rotation of a salinity composition](docs/media/en/05-spatial-rotation.gif)

1. Import a scene with explicit native 3D information. For layered maps, confirm the ranges and appearance using the “2D first, then 3D” workflow.
2. Enter the **full composition view** and open the 3D editing sidebar.
3. Enable “Synchronize rotation of unlocked panels”, then drag to rotate. Use the mouse wheel to zoom and Shift + drag to pan.
4. Apply when satisfied. Use “Reset 3D view” when you need a common starting view. The entire applied edit can be undone.

By default, only the current panel changes; synchronization requires an explicit choice. Compatible, unlocked native 3D panels participate, while retaining their own typography, colors, colorbars, proportions, zoom and pan. Relationships between multiple axes or unknown geometries are not inferred automatically.

PNGs, screenshots and flat SVGs do not contain a native camera that can be rotated. Adapt the source code and data first. See [3D integration](skills/figure-as-my-mind/references/3d-adapters.md) and the [synthetic 3D example](examples/spatial-demo/README.md); the original cruise data used in the demonstration is not required.

## 6. Reuse settings and choose a plotting language

**Goal: apply the style you just refined to another batch of figures with the same structure.**

![Choosing a language and copying settings](docs/media/en/06-reuse-settings.gif)

1. Click “Copy settings for Codex” above the canvas.
2. Choose R, Python, MATLAB or C. Copy the prompt and JSON, or download the JSON.
3. Return to the conversation, provide the target script and data, and specify which variables or groups should receive the settings.
4. Check axis limits, group colors and special objects. For figures with different structures, match semantic roles rather than blindly reusing object IDs.

For example:

```text
Use $figure-as-my-mind to apply the settings below to the response variables I select in this script.
Keep the original statistical methods and input data, group colors, and links between observations and error bars.
First list the available variables, and explain any special coordinates or incompatible objects.
After creating editable figures, return the workbench link and output code in the selected language.
```

Multilanguage vector reproduction replays the current appearance accurately. **It does not automatically translate statistical models between languages.** To change data or refit a model, continue from the actual inputs and original analysis script.

## 7. Save and export

**Goal: produce publication-ready images and keep the project editable for later.**

![Export settings and the resulting composition](docs/media/en/07-export.gif)

1. Wait for the autosaved status, then click “Export…”.
2. Choose a vector format such as SVG or PDF, or a raster format such as PNG or TIFF. Set the physical dimensions and DPI as applicable.
3. Exports are transparent by default. The workbench uses a white preview for readability; explicitly choose a white background if you need one in the output.
4. Select images and plotting code, images only, or plotting code only, and choose the target code language.
5. For a complete backup, export the project package. Reopen the same project path next time to retain the saved settings.

A vector export does not automatically convert an existing bitmap into vector geometry. The project, source snapshots, settings and reproduction scripts serve different purposes. Do not keep only the editor HTML or a temporary browser address.

## Choose a starting point

- **A new figure:** specify the plot type, data, variables and language. R is preferred when no language is specified, and semantic information is retained from the source.
- **Existing source code:** preserve the original analysis. Use native import for Python; for R/ggplot, export both the scene and SVG.
- **SVG only:** start with appearance edits. Numerical coordinate editing and linked statistical components require additional semantic information.
- **PNG/JPG only:** use the image as a reference, redraw it, then edit the result. Do not invent observations from pixels.

For multiple complex compositions, work through one composition at a time: edit its panels, confirm linked changes, arrange the layout, and finish it before moving to the next. This also reduces simultaneous rendering.

## Full demonstration and further reading

[Video with background music (Chinese demonstration)](docs/media/demo-bgm.mp4) · [Music attribution](docs/media/music-credit.txt) · [English GIF notes](docs/media/en/README.md)

The salinity figures demonstrate the interactions. The runnable CSV, R/Python and 3D examples in the repository use synthetic inputs; personal raw cruise files are not included. Use the real data, projection, model and statistical methods required by your own analysis.

[Full illustrated tutorial](skills/figure-as-my-mind/docs/教程.md) · [Four-language bridges](skills/figure-as-my-mind/references/native-coordinates.md) · [Project format](skills/figure-as-my-mind/references/project-format.md) · [MIT license](LICENSE)
