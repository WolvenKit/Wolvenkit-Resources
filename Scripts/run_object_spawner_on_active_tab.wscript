import {RunFileValidation} from "hook_global.wscript";
import * as Logger from 'Logger.wscript';
import {RunEntitySpawnerImport} from "./Internal/entSpawner/import_object_spawner.wscript";

// @author manavortex
// @version 1.0
// @type hook

RunEntitySpawnerImport(GetActiveFileRelativePath(), true);

function GetActiveFileRelativePath() {
	let absolutePath =  wkit.GetActiveDocument()?.FilePath;
	if (!absolutePath) return null;

	const relativePath = absolutePath.split('raw\\').pop();
	if (!relativePath || !wkit.FileExistsInRaw(relativePath)) {
		Logger.Error(`No open file found.`);
		return null;
	}
	return relativePath;
}