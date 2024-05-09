// Exports Collision shapes from StreamingSector files 
// @author Simarilius
// @version 0.1

import * as Logger from 'Logger.wscript';
import * as TypeHelper from 'TypeHelper.wscript';


export function Export_Sector_Collisions(data) {
Logger.Info('In Collisions')
Logger.Info(Object.keys(data['Data']['RootChunk']))
var sectorHashesSet = new Set(); // Creating a Set to store unique hashes
var shapeHashesSet = new Set(); // Creating a Set to store unique hashes

data["Data"]["RootChunk"]["nodes"].forEach(node => {
	if (node['Data']['$type']=='worldCollisionNode'){
		//Logger.Info(Object.keys(node['Data']))
		var sectorHash = node['Data']["sectorHash"].toString()
		//Logger.Info("Sector Hash: "+  sectorHash);
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
	         		shapeHashesSet.add(hash);
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

if (sectHashesLength==1) {
	shapeHashes.forEach(function(hash) {
	let json = wkit.ExportGeometryCacheEntry(sectorHashes[0],hash);
	wkit.SaveToRaw('collision_meshes\\' + sectorHashes[0] + '_' + hash + '.json', json);
	
	});
}

}