// Exports Collision shapes from StreamingSector files
// @author Simarilius
// @version 0.2

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';
let sectors = []

for (let filename of wkit.GetProjectFiles('archive')) {
        // Logger.Success(filename);
        if (filename.split('.').pop() === "streamingsector") {
            sectors.push(filename);
        }
    }

// loop over every sector in `sectors`
for (let sect in sectors) {
    Logger.Info(`Extracting Collision meshes for sector...\n${sectors[sect]}`);
    let file = wkit.GetFileFromProject(sectors[sect], OpenAs.GameFile);
    let json = TypeHelper.JsonParse(wkit.GameFileToJson(file));
    Export_Sector_Collisions(json);
}


export function Export_Sector_Collisions(data) {
Logger.Info('In Collisions')
Logger.Info(Object.keys(data['Data']['RootChunk']))
var sectorHashesSet = new Set(); // Creating a Set to store unique hashes
var shapeHashesSet = new Set(); // Creating a Set to store unique hashes

data["Data"]["RootChunk"]["nodes"].forEach(node => {
	if (node['Data']['$type']=='worldCollisionNode'){
		Logger.Info(Object.keys(node['Data']))
		var sectorHash = node['Data']["sectorHash"].toString()
		Logger.Info("Sector Hash: "+  sectorHash);
		sectorHashesSet.add(sectorHash);
		
		
		//Logger.Info(Object.keys(node["Data"]["compiledData"]["Data"]["Actors"]["0"]["Shapes"]["0"]));
	    var actors = node["Data"]["compiledData"]["Data"]["Actors"];
	    for (var actor in actors){
	    	 //Logger.Info(actor);
	         
	         for (var shape in actors[actor]['Shapes']){
	         	//Logger.Info("Shape");
	         	//Logger.Info(Object.keys(actors[actor]['Shapes'][shape]));
	         	
	         	if (Object.keys(actors[actor]['Shapes'][shape]).includes('Hash')){
	         		var hash=actors[actor]['Shapes'][shape]['Hash'].toString() ;
	         		//Logger.Info("Entry Hash: "+ hash);
	         		shapeHashesSet.add([sectorHash,hash]);
	         	}
	         }	         
	    }	    
	}	
});

var sectorHashes = Array.from(sectorHashesSet);
sectorHashes.forEach(function(hash) {
    Logger.Info("Sector Hash: " + hash);
});
var sectHashesLength = sectorHashesSet.size; // Getting the length of the Set

Logger.Info("Length of unique sector hashes: " + sectHashesLength);

var shapeHashes = Array.from(shapeHashesSet);
shapeHashes.forEach(function(hash) {
    Logger.Info("Entry Hash: " + hash);
});


shapeHashes.forEach(function(hash) {
let json = wkit.ExportGeometryCacheEntry(hash[0],hash[1]);
wkit.SaveToRaw('collision_meshes\\' + hash[0] + '_' + hash[1] + '.json', json);

});


}
