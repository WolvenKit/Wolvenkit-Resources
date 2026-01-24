import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';

/**
 * @typedef {Object} EntityInfo
 * @property {string} appFile
 * @property {string} appName
 * @property {string} filePath
 */

/**
 * returns a map entity appearance info from the file
 * <pre>
 * {
 *     "name": {  
 *       "appFile": "path_to_file.app",
 *       "appName": "path_to_file.app",
 *       "filePath": "path_to_file.ent"
 *     },
 * }
 * </pre>
 * @param filePath
 * @returns {{
 *     [key: string]: { appFile: string, appName: string, filePath: string }
 * }}
 */
export function Get_Entity_Appearances(filePath)
{
    const ret = {};
    // Parse referenced file and return factory info
    try {
        const file = wkit.GameFileToJson(wkit.GetFileFromProject(filePath, OpenAs.GameFile));
        let data = TypeHelper.JsonParse(file)?.Data?.RootChunk;

        if ((data?.appearances ?? []).length === 0) {
             return ret;
        }
        (data.appearances ?? {}).forEach((item) => {
           ret[item.name ?? ""] = {
               appFile: `${item.appearanceResource?.DepotPath?.value}`,
               appName: (item.appearanceName || item.name).value,
               filePath: filePath,
           };
        });
    } catch (e) {
        Logger.Error(`Error while parsing ${filePath}: ${e.message}`);
    }
    return ret;
}


export function Get_Entity_Type(filePath)
{
    // Parse referenced file and return entity type
    try {
        const file = wkit.GameFileToJson(wkit.GetFileFromProject(filePath, OpenAs.GameFile));
        let data = TypeHelper.JsonParse(file)?.Data?.RootChunk;
        return data?.entity?.Data?.$type;
    } catch (e) {
        return `Error while parsing ${filePath}: ${e.message}`;
    }    
}

