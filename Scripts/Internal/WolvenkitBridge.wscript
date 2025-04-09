// @type lib
// @name WolvenkitBridge.wscript
// @description Keep all wkit. function calls in this file and access them via import. This will avoid noise from linting and validation.

export function FileExists(depotPath) {
    return wkit.FileExists(depotPath);
}
export function FileExistsInProject(depotPath) {
    return wkit.FileExistsInProject(depotPath); 
}
export function SuspendFileWatcher() {
    return wkit.SuspendFileWatcher();
}
export function LoadGameFileFromProject(filePath, fileExtension) {
    return wkit.LoadGameFileFromProject(filePath, fileExtension);
}
export function CreateInstanceAsJSON(className) {
    return wkit.CreateInstanceAsJSON(className);
}
export function JsonToCR2W(jsonString) {
    return wkit.JsonToCR2W(jsonString);
}

export function OpenDocument(filePath) {
    return wkit.OpenDocument(filePath);
}

export function SaveToProject(activeFilePath, cr2wContent) {
    return wkit.SaveToProject(activeFilePath, cr2wContent);
}

/**
 * 
 * @returns {{ 
 *   FileName: string;
 *   FilePath: string | undefined;
 *   IsDirty: boolean;
 *   Close: () => VoidFunction;
 * }} | undefined
 */
export function GetActiveDocument() {
    return wkit.GetActiveDocument();
}

export function ShowMessageBox(messageText, messageTitle, img, buttons) {
    return wkit.ShowMessageBox(messageText, messageTitle, img, buttons);
}

