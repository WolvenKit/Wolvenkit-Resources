import * as Logger from '../../Logger.wscript';
import * as TypeHelper from '../../TypeHelper.wscript';

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