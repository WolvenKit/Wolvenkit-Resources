// @version 1.0
// @type hook
// @hook_extension global

import * as FileValidation from 'Wolvenkit_FileValidation.wscript';
import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';
import Settings from 'hook_settings.wscript';

/**
 * If this is set to "true" and file validation runs into any errors, then YOUR FILES WILL NO LONGER SAVE.
 * ONLY ENABLE THIS IF YOU KNOW WHAT YOU'RE DOING!
 */
const isWolvenkitDeveloper = true;

const README_URL = 'https://wiki.redmodding.org/wolvenkit/wolvenkit-app/file-validation';

globalThis.onSave = function (ext, file) {
    if (!Settings.Enabled) {
        return {
            success: true,
            file: file
        }
    }
    return RunFileValidation(ext, file);
}

const yamlExtensions = ['yaml', 'yml', 'xl', 'archive.xl'];

export function RunFileValidation(ext, file) {
    if (!file) { // Something went wrong when passing the file from WKit
        return;
    }
    
    let fileContent;
    
    const isYamlFile = yamlExtensions.includes(ext);
    if (isYamlFile) {
        try {
            fileContent = TypeHelper.JsonParse(wkit.YamlToJson(file));            
        } catch {
            if (!file.includes("[object Object]")) {
                Logger.Error(`${file} contains invalid YAML. Use www.yamllint.com to fix your syntax errors.`);                
            }
            return;
        }
    } else {
        fileContent = TypeHelper.JsonParse(file);        
    }

    if (!fileContent) {
        Logger.Error(`Failed to read file ${file}. Skipping file validation.`)
        return;
    }
    // grab file name from json and inform file validation about it
    const fileName = (fileContent.Header?.ArchiveFileName || '').split('archive\\').pop() || '';
    FileValidation.setPathToCurrentFile(fileName);

    wkit.SuspendFileWatcher(true);
    let success = true;
    try {
        let data;
        if (isYamlFile) {
            data = fileContent;
        } else {
            data = fileContent["Data"]["RootChunk"];            
        }
        switch (ext) {
            case "anims":
                FileValidation.validateAnimationFile(data, Settings.Anims);
                break;
            case "app":
                FileValidation.validateAppFile(data, Settings.App);
                break;
            case "csv":
                FileValidation.validateCsvFile(data, Settings.Csv);
                break;
            case "ent":
                FileValidation.validateEntFile(data, Settings.Ent);
                break;
            case "mesh":
                FileValidation.validateMeshFile(data, Settings.Mesh);
                break;
            case "morphtarget":
                FileValidation.validateMorphtargetFile(data, Settings.Morphtarget);
                break;
            case "mlsetup":
                FileValidation.validateMlsetupFile(data, {});
                break;
            case "mi":
                FileValidation.validateMiFile(data, Settings.Mi);
                break;
            case "mltemplate":
                FileValidation.validateMlTemplateFile(data, {});
                break;
            case "workspot":
                FileValidation.validateWorkspotFile(data, Settings.Workspot);
                file = TypeHelper.JsonStringify(fileContent);
                break;
            case "inkatlas":
                FileValidation.validateInkatlasFile(data, Settings.Inkatlas);
                file = TypeHelper.JsonStringify(fileContent);
                break;
            case "inkcharcustomization":
                FileValidation.validateInkCCFile(data, Settings.InkCC);
                file = TypeHelper.JsonStringify(fileContent);
                break;
            case "json":
                FileValidation.validateJsonFile(data, Settings.Json);
                file = TypeHelper.JsonStringify(fileContent);
                break;
            case "questphase":
                FileValidation.validateQuestphaseFile(data, Settings.GraphQuestphase);
                break;
            case "scene":
                FileValidation.validateSceneFile(data, Settings.GraphScene);
                break;
            case "archive.xl":
            case "xl":
            case "yml":
            case "yaml":
                FileValidation.validateYamlFile(data, {}, ext.endsWith('xl'));
                break;
            default:
                Logger.Info("File validation not implemented for file type " + ext);
        }
    } catch (err) {
        if (isWolvenkitDeveloper) {
            throw err;
        } else {            
            Logger.Warning(`Could not verify the file you just saved due to an error in wkit.`);
            Logger.Info('\tYou can ignore this warning or help us fix the problem: get in touch on Discord or create a ticket under https://github.com/WolvenKit/Wolvenkit/issues');
            Logger.Info('\tPlease include the necessary files from your project\'s source folder.')
            Logger.Info(`\tFor more information, check ${README_URL}#there-was-an-error`)
        }
    }
    if (FileValidation.hasUppercasePaths) {
        Logger.Error(`You have uppercase characters in your file paths. File validation will not work.`);
        Logger.Info(`If you are using this as a hack to disable the feature, see ${README_URL}.`)
    }

    wkit.SuspendFileWatcher(false);

    const retSuccess = {
        success: success,
        file: file
    }

    // either we have nothing to write or we aren't supposed to write => abort
    if (!FileValidation.isDataChangedForWriting || Settings.DisableAutofix) return retSuccess;

    const filePath = wkit.GetActiveDocument()?.FilePath ?? '';

    // unless it's a workspot, automatically close and re-open it
    if (!fileName.endsWith('workspot') || Settings.Workspot.autoReopenFile) {
        try {
            Logger.Info(`FileValidation: Reopening ${filePath} for you…`);
            wkit.GetActiveDocument()?.Close();
            wkit.OpenDocument(filePath);
        } catch (err) {
            Logger.Error(`Failed! Automatic changes won't be applied until you close and re-open your file!`);
        }
        return retSuccess;
    }

    if (fileName.endsWith('workspot')) {
        // tell the user why it's not auto-closing and -reopening
        Logger.Warning(`File validation has made the following changes:`);
        Logger.Info(`\t- fixed order of workspot indices`);
        Logger.Info(`To disable the feature, set "Workspot.fixIndexOrder" to "false".`);
        Logger.Info(`To disable this warning, set "Workspot.autoReopenFile" to "true".`);
        Logger.Info(`https://wiki.redmodding.org/wolvenkit/wolvenkit-app/file-validation#configuring-file-validation`);
    } else {
        Logger.Info(`File validation has made changes, but we forgot to keep track what it did.`);
        Logger.Info(`Please check the log output above. To make this error go away for good, `);
        Logger.Info(`get in touch via REDmodding Discord or create a ticket: https://github.com/WolvenKit/Wolvenkit/issues`);
    }

    Logger.Info(`You need to close and re-open ${filePath}, or file validation won't know about the automatic changes.`);
    return retSuccess;
}

globalThis.onExport = function (path, settings) {
    const json = TypeHelper.JsonParse(settings);
    return {
        settings: TypeHelper.JsonStringify(json)
    }
}

globalThis.onPreImport = function (path, settings) {
    const json = TypeHelper.JsonParse(settings);
    // Logger.Info(json);
    return {
        settings: TypeHelper.JsonStringify(json)
    }
}

// Not yet implemented
globalThis.onPostImport = function (path, settings) {
    Logger.Info(settings);
    return {
        success: true
    }
}

globalThis.onImportFromJson = function (jsonText) {
    const json = TypeHelper.JsonParse(jsonText);
    
    // json["Data"]["RootChunk"]["cookingPlatform"] = "PLATFORM_PS5";

    return {
        jsonText: TypeHelper.JsonStringify(json, 2)
    }
}

globalThis.onParsingError = function (jsonText) {
    const json = TypeHelper.JsonParse(jsonText);
    
    let isPatched = false;

    if (json["ExpectedType"] === "shadowsShadowCastingMode" && json["Value"]["$type"] === "Bool") {
    	isPatched = true;
    	
    	json["Value"]["$type"] = "shadowsShadowCastingMode";
    	if (json["Value"]["Value"] === 0) {
    		json["Value"]["Value"] = "Never";
    	} else {
    		json["Value"]["Value"] = "Always";
    	}
    }
    
    if (!isPatched) {
    	Logger.Debug(json);
    }
    
    // Just an example
    // if(json["EnumType"] === "ECookingPlatform") { 
    // 	   isPatched = true;
    //     json["StringValue"] = "PLATFORM_PC";
    // }

    return {
    	isPatched : isPatched,
        jsonText: TypeHelper.JsonStringify(json)
    }
}
