// @author manavortex
// @version 1.0

import * as Logger from "./Logger.wscript";
import * as TypeHelper from "./TypeHelper.wscript";
export function WriteToActiveFile(meshData) {
    let activeDocument = wkit.GetActiveDocument();
    if (activeDocument === null) {
        return;
    }
    if (activeDocument.IsDirty) {
        const response = wkit.ShowMessageBox(`"${activeDocument.FileName}" has unsaved changes - are you sure you want to reopen this file?`, "Confirm", WMessageBoxImage.Question, WMessageBoxButtons.YesNo);
        if (response === WMessageBoxResult.No) {
            return;
        }
    }
    Logger.Success(meshData);

    const filePath = activeDocument.FilePath.split('archive\\').pop();
    wkit.SaveToProject(filePath, wkit.JsonToCR2W(TypeHelper.JsonStringify(meshData)));

    try {
        activeDocument.Close();
        wkit.OpenDocument(activeDocument.FilePath);
    } catch (err) {
        Logger.Error(`Failed! Automatic changes won't be applied until you close and re-open your file!`);
    }
}