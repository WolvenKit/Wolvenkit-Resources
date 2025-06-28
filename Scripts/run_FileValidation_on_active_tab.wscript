import {RunFileValidation} from "hook_global.wscript";
import * as Logger from 'Logger.wscript';

// @author manavortex
// @version 1.0
// @type hook

Run();
function Run() {
    const activeDocument = wkit.GetActiveDocument();
    if (!activeDocument) {
        Logger.Error('Failed to find active document');
        return;
    }
    
    let absolutePath = `${activeDocument.FilePath}`;
    if (!absolutePath) {
        Logger.Error('No file path in active document. Did you add this file to your project?');
        return;        
    }
    
    let activeFile, relativePath, fileExtension;
    
    
    if (absolutePath.endsWith(".xl")) {
        relativePath = absolutePath.split('resources\\').pop();
        activeFile = wkit.YamlToJson( wkit.LoadFromResources(relativePath));
    } else if (absolutePath.includes('archive\\')) {
        relativePath = absolutePath.split('archive\\').pop();

        if (!relativePath || !wkit.FileExists(relativePath)) {
            Logger.Error(`No open file found: ${relativePath}`);
            return;
        }

        activeFile = wkit.LoadGameFileFromProject(relativePath, 'json');

    } else {
        Logger.Error(`Can't parse files directly below 'archive'. Please put the file into a subfolder: ${absolutePath}`);        
    }
    

    fileExtension = (!relativePath || !relativePath.includes(".")) ? null :  relativePath.substring(relativePath.indexOf('.')+1);
    
    if (!activeFile) {
        Logger.Error(`Failed to load file from project: ${relativePath}`);
        return;
    }

    if (!fileExtension) {
        Logger.Error(`Failed to find file extension in: ${relativePath}`);
        return;
    }
    
    RunFileValidation(fileExtension, activeFile);    
}
