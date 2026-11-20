// Imports an entitySpawner json export
// @author keanuwheeze
// @version 1.0.8

//////////////// Modify this //////////////////

const inputFilePathInRawFolder = "new_project_exported.json"

///////////////////////////////////////////////

import * as Logger from 'Logger.wscript';

const version = "1.0.8"

const DEFAULT_NODE_FLAGS = "FLAG_AllowForceStreamIn, FLAG_Building"
const DEFAULT_STREAMING_PRIORITY = 50

const header = {
  "Header": {
    "WolvenKitVersion": "8.14.1",
    "WKitJsonVersion": "0.0.9",
	"GameVersion": 2500,
    "DataType": "CR2W",
  },
  "Data": {
    "Version": 195,
    "BuildVersion": 0,
    "RootChunk": {},
    "EmbeddedFiles": []
  }
}

// Helpers

const createNewFile = (type) => {
	let file = JSON.parse(JSON.stringify(header))
    file.Data.RootChunk = JSON.parse(wkit.CreateInstanceAsJSON(type))
	return file
}

const getNewSector = () => {
	let data = createNewFile("worldStreamingSector")
	data.Data.RootChunk.nodeData.Type = "WolvenKit.RED4.Archive.Buffer.worldNodeDataBuffer, WolvenKit.RED4, Version=10.0.0.0, Culture=neutral, PublicKeyToken=null"
	data.Data.RootChunk.nodeData.Data = []
	return data
}

const getNewDeviceFile = () => {
	let data = createNewFile("gameDeviceResource")
	data.Data.RootChunk.data = { "Data": { "$type": "gameDeviceResourceData", "unk1" : [], "version": 2 } }

	return data
}

const getNewPSFile = () => {
	let data = createNewFile("gamePersistentStateDataResource")
	data.Data.RootChunk.buffer = {
		"BufferId": "0",
		"Flags": 4063232,
        "Type": "WolvenKit.RED4.Archive.Buffer.RedPackage, WolvenKit.RED4, Version=8.13.0.0, Culture=neutral, PublicKeyToken=null",
        "Data": {
          "Version": 4,
          "Sections": 6,
          "CruidIndex": 0,
          "CruidDict": {},
          "Chunks": []
        }
	}

	return data
}

const getNewBlock = () => {
	return createNewFile("worldStreamingBlock")
}

const getNewWorldNodeData = () => {
	let data = {
		"$type": "worldCompiledNodeInstanceSetupInfo",
		"dataGroup": "Base",
		"externalInplaceResourceHash": {
			"DepotPath": { "$type": "ResourcePath", "$storage": "uint64", "$value": "0" },
			"Flags": "Default"
		},
		"globalNodeId": { "$type": "worldGlobalNodeID", "hash": "0" },
		"instanceIndex": 4294967295,
		"nodeFlags": "FLAG_AllowForceStreamIn, FLAG_Building",
		"nodeIdx": "0",
		"patchedNode": { "$type": "NodeRef", "$storage": "uint64", "$value": "0" },
		"preboostStreamingRefPoint": { "$type": "Vector3", "X": 0, "Y": 0, "Z": 0 },
		"proxyMeshId": { "$type": "worldGlobalNodeID", "hash": "0" },
		"scale": { "$type": "Vector3", "X": 0, "Y": 0, "Z": 0 },
		"secondaryRefPointDistance": 0,
		"secondaryRefPointPosition": { "$type": "Vector3", "X": 0, "Y": 0, "Z": 0 },
		"streamingDistance": 0,
		"streamingPriority": "1",
		"streamingRefPoint": { "$type": "Vector3", "X": 0, "Y": 0, "Z": 0 },
		"todvisMask": "0",
		"transform": {
			"$type": "Transform",
			"orientation": { "$type": "Quaternion", "i": 0, "j": 0, "k": 0, "r": 1 },
			"position": { "$type": "Vector4", "W": 0, "X": 0, "Y": 0, "Z": 0 }
		}
	}
    return JSON.parse(JSON.stringify(data))
}

const deepCopy = (origin, target) => {
    for (let key in origin) {
        if (typeof origin[key] === 'object' && origin[key] !== null) {
            if (!target[key]) {
                target[key] = Array.isArray(origin[key]) ? [] : {};
            }
            deepCopy(origin[key], target[key]);
        } else {
            target[key] = origin[key];
        }
    }
}

function fnv1a64NodeRef(value) {
	value = value.replace(/#/g, "");

    let hash = 0xcbf29ce484222325n;
    const prime = 0x100000001b3n;

    for (let i = 0; i < value.length; i++) {
        const code = value.charCodeAt(i);
        const byte = code <= 0x7f ? code : 0x3f;
        hash = BigInt.asUintN(64, (hash ^ BigInt(byte)) * prime);
    }

    return hash;
}

const insertNode = (sector, node) => {
	let nodeData = getNewWorldNodeData()
	let streamingRefPoint = node.streamingRefPoint || node.position

	nodeData.nodeIdx = sector.Data.RootChunk.nodes.length.toString()
	
	// Position
	nodeData.transform.position.X = node.position.x
	nodeData.transform.position.Y = node.position.y
	nodeData.transform.position.Z = node.position.z
	
	// Streaming values
	nodeData.secondaryRefPointDistance = node.secondaryRange
	nodeData.streamingDistance = node.primaryRange

	// Flags and priority
	nodeData.nodeFlags = node.nodeFlags ?? DEFAULT_NODE_FLAGS
	nodeData.streamingPriority = node.streamingPriority ?? DEFAULT_STREAMING_PRIORITY

	// Streaming reference points
	nodeData.secondaryRefPointPosition.X = streamingRefPoint.x
	nodeData.secondaryRefPointPosition.Y = streamingRefPoint.y
	nodeData.secondaryRefPointPosition.Z = streamingRefPoint.z

	nodeData.streamingRefPoint.X = streamingRefPoint.x
	nodeData.streamingRefPoint.Y = streamingRefPoint.y
	nodeData.streamingRefPoint.Z = streamingRefPoint.z

	nodeData.preboostStreamingRefPoint.X = node.position.x
	nodeData.preboostStreamingRefPoint.Y = node.position.y
	nodeData.preboostStreamingRefPoint.Z = node.position.z

	// Scale
	nodeData.scale.X = node.scale.x
	nodeData.scale.Y = node.scale.y
	nodeData.scale.Z = node.scale.z
	
	// Rotation
	nodeData.transform.orientation.i = node.rotation.i
	nodeData.transform.orientation.j = node.rotation.j
	nodeData.transform.orientation.k = node.rotation.k
	nodeData.transform.orientation.r = node.rotation.r
	
	// NodeRef/global node ID
	if (node.nodeRef !== undefined && node.nodeRef !== "") {
		nodeData.globalNodeId.hash = fnv1a64NodeRef(node.nodeRef).toString()
		sector.Data.RootChunk.nodeRefs.push({
			"$type": "NodeRef",
			"$storage": "string",
			"$value": node.nodeRef
		})
	} else {
		nodeData.globalNodeId.hash = wkit.HashString(JSON.stringify(nodeData), "fnv1a64").toString()
	}

	sector.Data.RootChunk.nodeData.Data.push(nodeData)
	
	let worldNode = JSON.parse(wkit.CreateInstanceAsJSON(node.type))
	
	sortInstanceData(node.data)
	deepCopy(node.data, worldNode)

	// Debug name for wkit
	worldNode.debugName.$value = node.name || ""

	sector.Data.RootChunk.nodes.push({HandleId : sector.Data.RootChunk.nodes.length.toString() , Data : worldNode})
}

const createSectorFromData = (data) => {
	let sector = getNewSector()
	sector.Data.RootChunk.category = data.category
	sector.Data.RootChunk.level = data.level
	sector.Data.RootChunk.variantIndices = [0]
	sector.Data.RootChunk.version = 68
	sector.Data.RootChunk.cookingPlatform = "PLATFORM_PC"

	if (data.variantIndices !== undefined) {
		sector.Data.RootChunk.variantIndices = data.variantIndices
	}

	return sector
}

const addSectorToBlock = (block, info, root) => {
	let descriptor = JSON.parse(wkit.CreateInstanceAsJSON("worldStreamingSectorDescriptor"))
	descriptor.category = info.category
	descriptor.level = info.level

	descriptor.numNodeRanges = 1 + (info.variants !== undefined ? info.variants.length : 0)
	
	descriptor.streamingBox.Max.X = info.max.x
	descriptor.streamingBox.Max.Y = info.max.y
	descriptor.streamingBox.Max.Z = info.max.z
	
	descriptor.streamingBox.Min.X = info.min.x
	descriptor.streamingBox.Min.Y = info.min.y
	descriptor.streamingBox.Min.Z = info.min.z
	
	descriptor.data.DepotPath.$storage = "string"
	descriptor.data.DepotPath.$value = `${root}/sectors/${info.name}.streamingsector`

	if (info.prefabRef !== undefined && info.prefabRef !== "") {
		descriptor.questPrefabNodeRef.$storage = "string"
		descriptor.questPrefabNodeRef.$value = info.prefabRef
	}

	if (info.variants !== undefined) {
		info.variants.forEach((variant) => {
			let variantData = JSON.parse(wkit.CreateInstanceAsJSON("worldStreamingSectorVariant"))

			variantData.enabledByDefault = variant.defaultOn
			variantData.name.$value = variant.name
			variantData.nodeRef.$storage = "string"
			variantData.nodeRef.$value = variant.ref
			variantData.rangeIndex = variant.index
			variantData.variantId = Math.abs(~~wkit.HashString(variant.ref + variant.name, "fnv1a32"))

			descriptor.variants.push(variantData)
		})
	}

	block.Data.RootChunk.descriptors.push(descriptor)
}

// Encodes the Human triangle tile variant read by WolvenKit's TilesReader.
// Additive Human tiles can link along matching borders.
const tileSize = 32.4;
const human = { height: 1.8, radius: 0.3, climb: 0.6 };

function vector([X, Y, Z]) {
    return { $type: "Vector4", X, Y, Z, W: 0 };
}

function box(min, max) {
    return { $type: "Box", Min: vector(min), Max: vector(max) };
}

// ClearScript's V8 host supplies typed arrays, but browser btoa is optional.
function base64(bytes) {
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let result = "";
    for (let i = 0; i < bytes.length; i += 3) {
        const value = (bytes[i] << 16) | ((bytes[i + 1] || 0) << 8) | (bytes[i + 2] || 0);
        result += alphabet[(value >>> 18) & 63] + alphabet[(value >>> 12) & 63];
        result += i + 1 < bytes.length ? alphabet[(value >>> 6) & 63] : "=";
        result += i + 2 < bytes.length ? alphabet[value & 63] : "=";
    }
    return result;
}

function binary(size) {
    const data = new DataView(new ArrayBuffer(size));
    let offset = 0;
    return {
        u8(value) { data.setUint8(offset, value); offset += 1; },
        u16(value) { data.setUint16(offset, value, true); offset += 2; },
        i32(value) { data.setInt32(offset, value, true); offset += 4; },
        f32(value) { data.setFloat32(offset, value, true); offset += 4; },
        zeros(count) { offset += count; },
        buffer() {
            if (offset !== size) throw new Error(`Buffer size mismatch: ${offset} vs ${size}`);
            return { BufferId: "1", Flags: 0, Bytes: base64(new Uint8Array(data.buffer)) };
        }
    };
}

function faceNeighbors(faces) {
    const edges = new Map();
    const neighbors = faces.map(() => [0, 0, 0]);
    for (const [index, face] of faces.entries()) {
        for (let slot = 0; slot < 3; slot++) {
            const a = face[slot];
            const b = face[(slot + 1) % 3];
            const edge = a < b ? `${a}:${b}` : `${b}:${a}`;
            const prior = edges.get(edge);
            if (prior) {
                if (prior.a === a || neighbors[prior.index][prior.slot] !== 0) {
                    throw new Error("Fitted triangles overlap or share a non-manifold edge.");
                }
                neighbors[index][slot] = prior.index + 1;
                neighbors[prior.index][prior.slot] = index + 1;
            } else {
                edges.set(edge, { index, slot, a });
            }
        }
    }
    return neighbors;
}

function boundsOf(points) {
    return [Math.min, Math.max].map(bound => [0, 1, 2].map(axis => bound(...points.map(p => p[axis]))));
}

function writeBoundsTree(buffer, vertices, faces, tileMin, quantization) {
    const faceBounds = faces.map(face => boundsOf(face.map(i => vertices[i])));
    // Preorder BV nodes have negative subtree escape indices. Leaves refer to faces.
    function writeSubtree(start, end) {
        const [min, max] = boundsOf(faceBounds.slice(start, end).flat());
        for (const point of [min, max]) {
            point.forEach((value, axis) => buffer.u16(Math.max(0, Math.floor((value - tileMin[axis]) * quantization))));
        }
        const count = end - start;
        buffer.i32(count === 1 ? start : -(2 * count - 1));
        if (count > 1) {
            const middle = start + Math.floor(count / 2);
            writeSubtree(start, middle);
            writeSubtree(middle, end);
        }
    }
    writeSubtree(0, faces.length);
    buffer.zeros(16); // Native allocation includes one trailing BV slot.
}

function validateNavigation(surface) {
    const { version, anchor, layer, vertices, faces } = surface ?? {};
    const triple = p => Array.isArray(p) && p.length === 3;
    const point = p => triple(p) && p.every(Number.isFinite);
    if (version !== 1 || !Number.isInteger(layer) || layer < 1 || layer > 255 || !point(anchor) || !Array.isArray(vertices) ||
        !vertices.length || vertices.length > 2048 || !vertices.every(point) ||
        !Array.isArray(faces) || !faces.length || faces.length > 2048 ||
        !faces.every(f => triple(f) && f.every(i => Number.isInteger(i) && i >= 0 && i < vertices.length))) {
        throw new Error("Invalid World Builder fitted-surface export.");
    }
    // RED world X/Y/Z becomes VAND X/Z/Y. Triangles use clockwise winding in XY.
    for (const [i, j, k] of faces) {
        const [a, b, c] = [vertices[i], vertices[j], vertices[k]];
        if ((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]) >= 0) {
            throw new Error("Fitted triangles must have clockwise, nondegenerate XY winding.");
        }
    }
    return { anchor, layer, vertices: vertices.map(([x, y, z]) => [x, z, y]), faces };
}

function createFittedNavigationResource(surface) {
    const { vertices, faces, anchor, layer } = validateNavigation(surface);
    const [min, max] = boundsOf(vertices);
    const [tx, ty] = surface.coords ?? [Math.floor(min[0] / tileSize), Math.floor(min[2] / tileSize)];
    const tileMin = [tx * tileSize, min[1] - 1, ty * tileSize];
    const tileMax = [(tx + 1) * tileSize, max[1] + human.height, (ty + 1) * tileSize];
    const tolerance = 1e-6;
    const inTile = (axis) => surface.coords
        ? min[axis] >= tileMin[axis] - tolerance && max[axis] <= tileMax[axis] + tolerance
        : min[axis] > tileMin[axis] && max[axis] < tileMax[axis];
    if (!inTile(0) || !inTile(2)) {
        throw new Error("Fitted navigation vertices are outside the declared 32.4 m tile.");
    }
    const count = faces.length;
    const links = count * 3 + 2 * (surface.portals?.length ?? 0);
    const quantization = 10;
    const buffer = binary(100 + 12 * vertices.length + 20 * count + 16 * links +
        12 * count + 4 * count + 16 * (2 * count));
    for (const ch of "VAND") buffer.u8(ch.charCodeAt(0));
    // Version, tile coordinates, layer, user ID, polygon/vertex/link counts,
    // detail mesh/vertex/triangle counts, BV slots, off-mesh count and base.
    for (const field of [8, tx, ty, layer, 0, count, vertices.length,
        links, count, 0, count, 2 * count, 0, count]) buffer.i32(field);
    for (const field of [human.height, human.radius, human.climb,
        ...tileMin, ...tileMax, quantization]) buffer.f32(field);
    vertices.flat().forEach(buffer.f32);
    const neighbors = faceNeighbors(faces);
    for (const [face, edge, side] of surface.portals ?? []) {
        const axis = side === 0 || side === 4 ? 0 : 2;
        const bound = (side === 0 || side === 2 ? tileMax : tileMin)[axis];
        const vertexA = vertices[faces[face]?.[edge]];
        const vertexB = vertices[faces[face]?.[(edge + 1) % 3]];
        if (!Number.isInteger(face) || !Number.isInteger(edge) || edge < 0 || edge > 2 ||
            neighbors[face]?.[edge] !== 0 || ![0, 2, 4, 6].includes(side) || !vertexA || !vertexB ||
            Math.abs(vertexA[axis] - bound) > tolerance || Math.abs(vertexB[axis] - bound) > tolerance) {
            throw new Error("Invalid external tile edge.");
        }
        neighbors[face][edge] = 0x8000 | side;
    }
    for (const [i, face] of faces.entries()) {
        buffer.i32(0);
        face.forEach(buffer.u16);
        neighbors[i].forEach(buffer.u16);
        buffer.u16(3); // Traversable Human polygon flags.
        buffer.u8(3);  // Triangle.
        buffer.u8(1);  // Ground area/type.
    }
    buffer.zeros(16 * links);
    for (let i = 0; i < count; i++) {
        buffer.i32(0); // No extra detail vertices.
        buffer.i32(i); // First detail triangle.
        buffer.u8(0);
        buffer.u8(1);
        buffer.zeros(2);
    }
    for (let i = 0; i < count; i++) [0, 1, 2, 21].forEach(buffer.u8);
    writeBoundsTree(buffer, vertices, faces, tileMin, quantization);
    const local = ([x, z, y]) => [x - anchor[0], y - anchor[1], z - anchor[2]];
    return {
        $type: "worldNavigationTileResource", cookingPlatform: "PLATFORM_PC", agentSize: "Human",
        localBoundingBox: box(local(tileMin), local(tileMax)),
        tilesData: [{
            $type: "worldNavigationTileData", tileX: tx, tileY: ty,
            tileIndex: 0, bufferIndex: 0, agentSize: "Human", tileRef: "9223372036854775807"
        }],
        tileBuffers: [buffer.buffer()]
    };
}

function fittedNavigationTiles(navigation) {
    if (navigation?.version === 1 && !navigation.coords && !navigation.portals) return [navigation];
    const tiles = navigation?.tiles;
    if (navigation?.version !== 2 || !Array.isArray(tiles) || !tiles.length || tiles.length > 36) {
        throw new Error("Invalid fitted navigation tile list.");
    }
    const directions = new Map([[0, [1, 0]], [2, [0, 1]], [4, [-1, 0]], [6, [0, -1]]]);
    const seen = new Set();
    const portals = new Set();
    const reciprocal = [];
    for (const tile of tiles) {
        if (!Array.isArray(tile?.coords) || tile.coords.length !== 2 || !tile.coords.every(Number.isSafeInteger) ||
            (tile.portals !== undefined && !Array.isArray(tile.portals))) {
            throw new Error("Invalid fitted navigation tile coordinates or portal list.");
        }
        const [tx, ty] = tile.coords;
        const key = tile.coords.join(":");
        if (seen.has(key)) throw new Error("Fitted navigation contains a duplicate tile.");
        seen.add(key);
        for (const entry of tile.portals ?? []) {
            if (!Array.isArray(entry) || entry.length !== 3) throw new Error("Invalid fitted navigation portal.");
            const [face, edge, side] = entry;
            const indices = tile.faces?.[face];
            const a = tile.vertices?.[indices?.[edge]];
            const b = tile.vertices?.[indices?.[(edge + 1) % 3]];
            const offset = directions.get(side);
            if (!Number.isInteger(face) || !Number.isInteger(edge) || edge < 0 || edge > 2 ||
                !Array.isArray(a) || !Array.isArray(b) || !offset) {
                throw new Error("Invalid fitted navigation portal.");
            }
            const segment = [a.join(","), b.join(",")].sort().join(";");
            portals.add(`${key}:${side}:${segment}`);
            reciprocal.push(`${tx + offset[0]}:${ty + offset[1]}:${(side + 4) % 8}:${segment}`);
        }
    }
    if (reciprocal.some(key => !portals.has(key))) {
        throw new Error("Fitted navigation contains an unmatched tile portal.");
    }
    return tiles;
}

const prepareFittedNavigation = (block, data) => {
	const surfaces = fittedNavigationTiles(data.navigation)
	const name = "_fitted_human_navigation"
	if (data.sectors.some(sector => sector.name.toLowerCase() === name)) {
		throw new Error(`Sector name ${name} is reserved for fitted navigation.`)
	}
	const tiles = surfaces.map(surface => ({ surface, resource: createFittedNavigationResource(surface) }))
	const [min, max] = boundsOf(surfaces.map(surface => surface.anchor))
	const info = {
		name,
		category: "Navigation",
		level: 3,
		min: { x: min[0] - 80, y: min[1] - 80, z: min[2] - 80 },
		max: { x: max[0] + 80, y: max[1] + 80, z: max[2] + 80 }
	}
	const path = `${data.name}/sectors/${name}.streamingsector`
	const sector = createSectorFromData(info)
	sector.Data.RootChunk.localInplaceResource = []
	for (const { surface, resource } of tiles) {
		const [x, y, z] = surface.anchor
		const tileName = surface.coords ? `${name}_${surface.coords.map(n => n < 0 ? 'm' + -n : n).join('_')}` : name
		const resourceReference = {
			DepotPath: { $type: "ResourcePath", $storage: "string", $value: `${data.name}/sectors/${tileName}.navmesh` },
			Flags: "Embedded"
		}
		insertNode(sector, {
			type: "worldNavigationNode",
			name: "Fitted Human navigation",
			position: { x, y, z },
			scale: { x: 1, y: 1, z: 1 },
			rotation: { i: 0, j: 0, k: 0, r: 1 },
			primaryRange: 500,
			secondaryRange: 100,
			data: { navigationTileResource: resourceReference, isVisibleInGame: 1 }
		})
		// Preserve the per-tile node ID used by earlier imports.
		const tileIdentity = `${data.name}/sectors/${tileName}.streamingsector`
		sector.Data.RootChunk.nodeData.Data.at(-1).globalNodeId.hash = fnv1a64NodeRef(tileIdentity).toString()
		sector.Data.RootChunk.localInplaceResource.push(resourceReference)
		resource.tileBuffers[0].BufferId = (sector.Data.EmbeddedFiles.length + 1).toString()
		sector.Data.EmbeddedFiles.push({ FileName: resourceReference.DepotPath, Content: resource })
	}
	const file = wkit.JsonToCR2W(JSON.stringify(sector))
	if (!file) {
		throw new Error("WolvenKit could not serialize the fitted Navigation sector.")
	}
	addSectorToBlock(block, info, data.name)
	const descriptor = block.Data.RootChunk.descriptors.at(-1)
	descriptor.streamingBox.Min.W = -3.402823466e38
	descriptor.streamingBox.Max.W = 3.402823466e38
	return { path, file }
}

const sortInstanceData = (data) => {
	if (data["instanceData"]) {
		const instanceDataSorted = []

		for (const dataEntry of data["instanceData"]["Data"]["buffer"]["Data"]["Chunks"]) {
			if (dataEntry["id"] == undefined) {
				instanceDataSorted.push(dataEntry)
			}
		}

		for (const dictKey in data["instanceData"]["Data"]["buffer"]["Data"]["CruidDict"]) {
			for (const dataEntry of data["instanceData"]["Data"]["buffer"]["Data"]["Chunks"]) {
				if (dataEntry["id"] === data["instanceData"]["Data"]["buffer"]["Data"]["CruidDict"][dictKey]) {
					instanceDataSorted.push(dataEntry)
				}
			}
		}

		data["instanceData"]["Data"]["buffer"]["Data"]["Chunks"] = instanceDataSorted
	}
}

//TODO: Put these in a list
// BufferID - Flags - Type - Data

const reorderJSONByType = (data) => {
    if (Array.isArray(data)) {
        return data.map(reorderJSONByType)
    } else if (data !== null && typeof data === "object") {
        const reordered = {};
        const keys = Object.keys(data);

        if (keys.includes("$type")) {
            reordered["$type"] = data["$type"];
        }
		if (keys.includes("ShapeType")) {
            reordered["ShapeType"] = data["ShapeType"];
        }
        if (keys.includes("BufferId")) {
            reordered["BufferId"] = data["BufferId"];
        }
        if (keys.includes("Flags")) {
            reordered["Flags"] = data["Flags"];
        }
        if (keys.includes("Type")) {
            reordered["Type"] = data["Type"];
        }

        for (let key of keys) {
            if (key !== "$type" && key !== "ShapeType" && key !== "Type" && key !== "BufferId" && key !== "Flags") {
                reordered[key] = reorderJSONByType(data[key]);
            }
        }

        return reordered;
    } else {
        return data;
    }
}

// Main import logic
export function RunEntitySpawnerImport(filePath = inputFilePathInRawFolder, calledFromExternal = false) {
	if (!filePath) {
		Logger.Error("No file path provided!")
		return;
	}

	if (!calledFromExternal && (!filePath || !wkit.FileExistsInRaw(filePath))) {
		return;
	}

	if (!wkit.FileExistsInRaw(filePath)) {
		Logger.Error(`File ${filePath} does not exist! Make sure the file sits either in the root of the raw folder, or adjust the inputFilePathInRawFolder variable accordingly.`)
		return;
	}
	
	Logger.Success(`Starting to import ${filePath}`);
	let data = JSON.parse(wkit.LoadRawJsonFromProject(filePath, "json"))

	data = reorderJSONByType(data)

	if (data == null) {
		Logger.Error(`File ${filePath} does not exist / wrong format!`)
	} else {
		if (data.version && data.version > version) {
			Logger.Error(`File ${filePath} requires import script version ${data.version} or higher, but script version is ${version}.`)
			return
		}

		let block = getNewBlock()
		let navigation
		if (data.navigation !== undefined) {
			try {
				navigation = prepareFittedNavigation(block, data)
			} catch (error) {
				Logger.Error(`Invalid fitted navigation in ${filePath}: ${error.message}`)
				return
			}
		}

		data.sectors.forEach((entry) => {
			addSectorToBlock(block, entry, data.name)
			let sector = createSectorFromData(entry)

			entry.nodes.forEach((node) => {
				insertNode(sector, node)
			})

			wkit.SaveToProject(`${data.name}/sectors/${entry.name}.streamingsector`, wkit.JsonToCR2W(JSON.stringify(sector)))
		})

		let hasDevices = data.devices !== undefined && Object.keys(data.devices).length > 0
		let hasPS = data.psEntries !== undefined && Object.keys(data.psEntries).length > 0

		if (hasDevices) {
			let devices = getNewDeviceFile()

			for (const [hash, device] of Object.entries(data.devices)) {
				devices.Data.RootChunk.data.Data.unk1.push({
					"$type": "gameDeviceResourceData_Cls1",
					"children": device.children,
					"className": {
						"$type": "CName",
						"$storage": "string",
						"$value": device.className
					},
					"hash": device.hash,
					"nodePosition": {
						"$type": "Vector3",
						"X": device.nodePosition.x,
						"Y": device.nodePosition.y,
						"Z": device.nodePosition.z
					},
					"parents": device.parents
				})
			}
			wkit.SaveToProject(`${data.name}/custom_devices.devices`, wkit.JsonToCR2W(JSON.stringify(devices)))
		}

		if (hasPS) {
			let ps = getNewPSFile()
			let index = 0
			for (const [_, entry] of Object.entries(data.psEntries)) {
				ps.Data.RootChunk.buffer.Data.Chunks.push(entry.instanceData)
				ps.Data.RootChunk.buffer.Data.CruidDict[index.toString()] = entry.PSID
				index++
			}
			wkit.SaveToProject(`${data.name}/custom_devices.psrep`, wkit.JsonToCR2W(JSON.stringify(ps)))
		}

		let xl = {
			streaming: {
				blocks: [
					`${data.name}/all.streamingblock`
				]
			}
		}

		if (hasDevices || hasPS) {
			xl.resource = {
				patch : {}
			}
		}
		if (hasDevices) {
			xl.resource.patch[`${data.name}/custom_devices.devices`] = [
				"base\\worlds\\03_night_city\\_compiled\\default\\03_night_city.devices"
			]
		}
		if (hasPS) {
			xl.resource.patch[`${data.name}/custom_devices.psrep`] = [
				"base\\worlds\\03_night_city\\_compiled\\default\\03_night_city.psrep"
			]
		}

		let xlBlob = JSON.stringify(xl)

		if (data.xlFormat == 1) {
			xlBlob = wkit.JsonToYaml(xlBlob)
		}

		if (navigation) {
			wkit.SaveToProject(navigation.path, navigation.file)
		}
		wkit.SaveToResources(`${data.name}.xl`, xlBlob)
		wkit.SaveToProject(`${data.name}/all.streamingblock`, wkit.JsonToCR2W(JSON.stringify(block)))

		Logger.Success("Import finished.")
	}
}

RunEntitySpawnerImport();
