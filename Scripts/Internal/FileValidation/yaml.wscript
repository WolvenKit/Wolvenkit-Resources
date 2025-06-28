import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';


function collectFilePaths(data, filePaths = []) {
    if (!data) {
        return filePaths;
    }
    let keys = Object.keys(data);
    if (keys.length === 0) {
        return filePaths;
    }
    for (let key of keys) {
        let value = data[key];
        if (typeof value === 'string' && ((value.includes('/')|| value.includes('\\') ) && value.includes('.'))) {
            filePaths.push(value);
        } else if (typeof value === 'object') {
            collectFilePaths(value, filePaths);
        }
    }
    return filePaths;
}

function verifyYamlFilePaths(data) {
    const filePaths = collectFilePaths(data);
    const projectFiles = TypeHelper.JsonParse(wkit.GetProjectFiles('archive'));

    const filesNotFound = filePaths.filter(p => !projectFiles.includes(p));

    if (filesNotFound.length > 0) {
        Logger.Error(`The following files were not found in the project:\n\t${filesNotFound.join('\n\t')}`);
    }
}

export function validate_yaml_file(data, yaml_settings, isXlFile = false) {

    if (isXlFile) {
        verifyYamlFilePaths(data);        
    }
}