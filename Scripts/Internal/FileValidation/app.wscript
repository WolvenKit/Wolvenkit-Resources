import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';
import { stringifyPotentialCName } from "./00_shared.wscript";

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
export function Get_App_Appearances(filePath)
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
           const itemName = stringifyPotentialCName((item.Data ?? {}).name);
           ret[itemName ?? ""] = {
               appFile: filePath,
               appName: itemName,
               filePath: filePath,
           };
        });
    } catch (e) {
        Logger.Error(`Error while parsing ${filePath}: ${e.message}`);
    }
    return ret;
}