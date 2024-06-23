import {RunFileValidation} from "hook_global.wscript";
import * as Logger from 'Logger.wscript';

// @author manavortex
// @version 1.0
// @type hook

RunFileValidation(GetActiveFileExtension(), ReadActiveFile());

function GetActiveFileRelativePath() {
    let absolutePath =  wkit.GetActiveDocument()?.FilePath;
    if (!absolutePath) return null; 
    
    const relativePath = absolutePath.split('archive\\').pop();
    if (!relativePath || !wkit.FileExists(relativePath)) {
        Logger.Error(`No open file found.`);
        return null;
    }
    return relativePath;
}


function ReadActiveFile() {
    const currentFileRelativePath = GetActiveFileRelativePath();
    if (!currentFileRelativePath || !wkit.FileExists(currentFileRelativePath)) {
        Logger.Error(`No open file found. Please switch to your currently-active file and try again!`);
        return null;
    }

    return wkit.LoadGameFileFromProject(currentFileRelativePath, 'json');
}


export function GetActiveFileExtension() {
    const relativePath = wkit.GetActiveDocument()?.FilePath;
    if (!relativePath) return null;
    const fileName = relativePath.split('archive\\').pop()
    if (!fileName || !fileName.includes(".")) return null;
    return fileName.substring(fileName.indexOf('.')+1);
}