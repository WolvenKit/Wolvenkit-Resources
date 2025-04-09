// @author manavortex
// @version 1.0
// @type lib

import * as Logger from "../Logger.wscript";
import * as TypeHelper from "../TypeHelper.wscript";
import * as Wolvenkit from "./WolvenkitBridge.wscript";
export function WriteToActiveFile(jsonData, reopenFile=true) {
    let activeDocument = Wolvenkit.GetActiveDocument();
    if (activeDocument === null) {
        Logger.Error("No active document…")
        return;
    }
    if (activeDocument.IsDirty) {
        const response = Wolvenkit.ShowMessageBox(`"${activeDocument.FileName}" has unsaved changes - are you sure you want to reopen this file?`, "Confirm", WMessageBoxImage.Question, WMessageBoxButtons.YesNo);
        if (response === WMessageBoxResult.No) {
            return;
        }
    }

    const activeFilePath = GetActiveFileRelativePath();
    let jsonString = '';
    try {
        jsonString = TypeHelper.JsonStringify(jsonData);                
    } catch (err) {
        Logger.Error(`Couldn't parse active file content to json:`);
        Logger.Error(err);
        return;
    } 
    let cr2wContent = null;
    try {
        cr2wContent = Wolvenkit.JsonToCR2W(jsonString)
    } catch (err) {
        Logger.Error(`Couldn't parse active file content to cr2w:`);
        Logger.Error(err);
        return;
    }

    try {
        Wolvenkit.SaveToProject(activeFilePath, cr2wContent); 
    } catch (err) {
        Logger.Error(`Couldn't save ${activeFilePath}:`);
        Logger.Error(err);
        return;
    }    

    if (!reopenFile) return;
    
    try {
        activeDocument.Close();
        Wolvenkit.OpenDocument(activeDocument.FilePath);
    } catch (err) {
        Logger.Error(`Failed re-opening the active file! Automatic changes won't be applied until you close and re-open your file!`);
    }
}

export function GetActiveFileAbsolutePath() {
    return Wolvenkit.GetActiveDocument()?.FilePath;
}
    
export function GetActiveFileRelativePath() {
    let absolutePath = GetActiveFileAbsolutePath();
    if (!absolutePath) return null; 
    
    const relativePath = absolutePath.split('archive\\').pop();
    if (!relativePath || !Wolvenkit.FileExists(relativePath)) {
        Logger.Error(`No open file found.`);
        return null;
    }
    return relativePath;
}
export function GetActiveFileExtension() {
    const relativePath = GetActiveFileRelativePath();
    if (!relativePath) return null;
    const fileName = relativePath.split('archive\\').pop()
    if (!fileName || !fileName.includes(".")) return null;
    return fileName.substring(fileName.indexOf('.'));
}

export function ReadActiveFileAsJson(expectedFileExtension, suppressLogOutput = false) {
    const activeDocument = Wolvenkit.GetActiveDocument(); 
    if (!activeDocument || !!expectedFileExtension && !activeDocument.FilePath?.endsWith(expectedFileExtension)) {
        if (!suppressLogOutput) Logger.Error(`Please run with a ${expectedFileExtension} file open in Wolvenkit!`);
        return null;
    }

    const currentFileRelativePath = GetActiveFileRelativePath();
    if (!currentFileRelativePath || !Wolvenkit.FileExists(currentFileRelativePath)) {
        if (!suppressLogOutput) Logger.Error(`No open file found. Please switch to your currently-active ${expectedFileExtension} and run this script from the menu!`);
        return null;
    }

    try {
        const fileContent = Wolvenkit.LoadGameFileFromProject(currentFileRelativePath, 'json');
        return TypeHelper.JsonParse(fileContent);
    } catch (err) {
        Logger.Error(`failed to parse ${expectedFileExtension} file at ${currentFileRelativePath}. Make sure the path is correct.`);
    }
    return null;
}