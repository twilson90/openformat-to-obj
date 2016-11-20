import sys, os, random, re, time, glob2, argparse
import xml.etree.ElementTree as ET
from enum import Enum

VALID_IMAGE_EXTS = [".png", ".tga", ".dds", ".jpg", ".jpeg"]
VALID_PATH_REGEX = re.compile(r"^[\\\w\-. ]+$")
owd = os.getcwd()
VERSION = "0.12"
OBJ_FIRST_LINE = "# V %s" % VERSION

class D3DDECLUSAGE(Enum):
	D3DDECLUSAGE_POSITION      = 0,
	D3DDECLUSAGE_BLENDWEIGHT   = 1,
	D3DDECLUSAGE_BLENDINDICES  = 2,
	D3DDECLUSAGE_NORMAL        = 3,
	D3DDECLUSAGE_PSIZE         = 4,
	D3DDECLUSAGE_TEXCOORD      = 5,
	D3DDECLUSAGE_TANGENT       = 6,
	D3DDECLUSAGE_BINORMAL      = 7,
	D3DDECLUSAGE_TESSFACTOR    = 8,
	D3DDECLUSAGE_POSITIONT     = 9,
	D3DDECLUSAGE_COLOR         = 10,
	D3DDECLUSAGE_FOG           = 11,
	D3DDECLUSAGE_DEPTH         = 12,
	D3DDECLUSAGE_SAMPLE        = 13

class D3DCOMPONENT(Enum):
	def __init__(self, id, len):
		self.id = id
		self.len = len

class D3DDECLTYPE(Enum):
	D3DDECLTYPE_FLOAT1     = 0,
	D3DDECLTYPE_FLOAT2     = 1,
	D3DDECLTYPE_FLOAT3     = 2,
	D3DDECLTYPE_FLOAT4     = 3,
	D3DDECLTYPE_D3DCOLOR   = 4,
	D3DDECLTYPE_UBYTE4     = 5,
	D3DDECLTYPE_SHORT2     = 6,
	D3DDECLTYPE_SHORT4     = 7,
	D3DDECLTYPE_UBYTE4N    = 8,
	D3DDECLTYPE_SHORT2N    = 9,
	D3DDECLTYPE_SHORT4N    = 10,
	D3DDECLTYPE_USHORT2N   = 11,
	D3DDECLTYPE_USHORT4N   = 12,
	D3DDECLTYPE_UDEC3      = 13,
	D3DDECLTYPE_DEC3N      = 14,
	D3DDECLTYPE_FLOAT16_2  = 15,
	D3DDECLTYPE_FLOAT16_4  = 16,
	D3DDECLTYPE_UNUSED     = 17,

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("openformat_convert.log", "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        pass  

def parse_odr(path, force=False):

	os.chdir(owd)
	full_path = os.path.realpath(path)
	name, ext = os.path.splitext(os.path.basename(full_path))
	dirname = os.path.dirname(full_path)
	filename = os.path.basename(full_path)
	obj_path = name+".obj"
	mtl_path = name+".mtl"

	if ext != ".odr":
		print("'%s' is not an ODR file" % path)
		return

	os.chdir(dirname)
	times = []
	times.append(time.time())

	if not force:
		if os.path.isfile(obj_path):
			with open(obj_path, 'r') as f:
				first_line = f.readline()
				if first_line == OBJ_FIRST_LINE+"\n":
					print("Skipping '%s'..." % path)
					return

	print("Converting '%s'..." % path)

	odr_data = readfile(full_path)
	shader_datas = re.findall(r"Shaders\s+{([\s\S]+?)^\t}", odr_data, re.MULTILINE)
	shader_datas = re.findall(r"(.+)\s+{([\s\S]+?)}", shader_datas[0], re.MULTILINE)
	shaders = []

	for d in shader_datas:
		shader_name = d[0].strip()

		diffuse = re.findall(r"DiffuseSampler\s+(.+)", d[1])
		bump = re.findall(r"BumpSampler\s+(.+)", d[1])
		spec = re.findall(r"SpecSampler\s+(.+)", d[1])
		textures = {
			"diffuse" : diffuse[0] if len(diffuse)>0 else None,
			"bump" : bump[0] if len(bump)>0 else None,
			"spec" : spec[0] if len(spec)>0 else None,
		}
		for k in textures:
			otx_path = textures[k]
			
			if otx_path is None:
				continue

			if not VALID_PATH_REGEX.match(otx_path):
				print("'%s' is not a valid path" % otx_path)
				continue

			if not os.path.isfile(otx_path):
				if os.path.splitext(otx_path)[1] != ".otx":
					print("Sampler '%s' did not specify location. Searching..." % otx_path)

					otx_name = os.path.basename(otx_path)
					otx_files = [
						os.path.join(otx_path+".otx"),
						os.path.join(otx_path, otx_name+".otx"),
						os.path.join("..", otx_path, otx_name+".otx"),
					]
					otx_files = [p for p in otx_files if os.path.isfile(p)]

					if len(otx_files) == 0:
						otx_files = glob2.glob("*/" + otx_name + ".otx")

					if len(otx_files) == 0:
						print("Could not find a matching path")
						continue
					else:
						otx_path = otx_files[0]
						print("Found '%s'" % otx_path)

			path_split = os.path.split(otx_path)
			hidr_path = os.path.join(path_split[0]+"+hidr", *path_split[1:])
			hi_path = os.path.join(path_split[0]+"+hi", *path_split[1:])

			if os.path.isfile(hidr_path):
				otx_path = hidr_path
			elif os.path.isfile(hi_path):
				otx_path = hi_path

			otx_data = readfile(otx_path)

			image_path = re.findall(r"^\s+Image (.+)$", otx_data, re.MULTILINE)[0]

			textures[k] = os.path.join(os.path.dirname(otx_path), image_path)

		shader = {
			"name" : "%s_%d" % (name, len(shaders)),
			"shader_name" : shader_name,
			"textures" : textures,
			"xml" : shader_manager_xml.find("./Shaders/ShaderPreSet[@name='%s']" % shader_name),
		}

		shaders.append(shader)

	lod_data = re.findall(r"LodGroup\s+{([\s\S]+?)^\t}", odr_data, re.MULTILINE)
	high_lod_data = re.findall(r"High [\s\S]+?{([\s\S]+?)}", lod_data[0], re.MULTILINE)
	med_lod_data = re.findall(r"Med [\s\S]+?{([\s\S]+?)}", lod_data[0], re.MULTILINE)
	low_lod_data = re.findall(r"Low [\s\S]+?{([\s\S]+?)}", lod_data[0], re.MULTILINE)
	vlow_lod_data = re.findall(r"Vlow [\s\S]+?{([\s\S]+?)}", lod_data[0], re.MULTILINE)

	lods = {
		"high" : high_lod_data[0] if len(high_lod_data)>0 else None,
		"med" : med_lod_data[0] if len(med_lod_data)>0 else None,
		"low" : low_lod_data[0] if len(low_lod_data)>0 else None,
		"vlow" : vlow_lod_data[0] if len(vlow_lod_data)>0 else None,
	}

	obj_data = ""
	mtl_data = ""
	index_offset = 1
			
	obj_data += OBJ_FIRST_LINE+"\n"
	obj_data += "\n"

	for k in lods:
		if lods[k] is None:
			continue

		lods[k] = [re.split(r"\s", s.strip())[0] for s in lods[k].splitlines()]
		lods[k] = [s for s in lods[k] if s != ""]

		for mesh_path in lods[k]:

			mesh_data = readfile(mesh_path)

			skinned = re.findall(r"Skinned (.+)", mesh_data)[0]
			gemoetry_datas = re.findall(r"Geometry\s+?{([\s\S]+?)^\t\t}", mesh_data, re.MULTILINE)

			obj_data += "mtllib %s\n" % mtl_path
			obj_data += "\n"
			
			geom_id = 0
			for geom_data in gemoetry_datas:

				geom_id += 1
				shader_index = int(re.findall(r"ShaderIndex (.+)", geom_data)[0])

				indices = re.findall(r"Indices \d+\s+{([\s\S]+?)}", geom_data)[0].strip()
				indices = re.split(r"\s+", indices)
				vertices = re.findall(r"Vertices \d+\s+{([\s\S]+?)}", geom_data)[0].strip()
				vertices = re.split(r"\n+", vertices)
				for i,v in enumerate(vertices):
					parts = vertices[i].split("/")
					parts = [p.strip().split(" ") for p in parts]
					vertices[i] = parts

				shader = shaders[shader_index]

				item_xml = shader["xml"].find("./VertexDeclarations/Item[@skinned='%s']" % skinned)
				elements_xml = item_xml.findall("./Element")

				ci = [0, 0, 0] #component_indices

				for i,e in enumerate(elements_xml):
					usage = e.get("usage")
					if usage == D3DDECLUSAGE.D3DDECLUSAGE_POSITION.name:
						ci[0] = i
					elif usage == D3DDECLUSAGE.D3DDECLUSAGE_NORMAL.name:
						ci[1] = i
					elif usage == D3DDECLUSAGE.D3DDECLUSAGE_TEXCOORD.name:
						ci[2] = i

				filtered_vertices = [[v[ci[0]], v[ci[1]], v[ci[2]]] for v in vertices]

				obj_data += "o %s_%s_%s\n" % (name, k, geom_id)
				obj_data += "\n"
				obj_data += "usemtl %s\n" % shader["name"]
				obj_data += "\n"
				for v in filtered_vertices:
					obj_data += "v "+" ".join(v[0])+"\n"
				obj_data += "\n"
				for v in filtered_vertices:
					obj_data += "vn "+" ".join(v[1])+"\n"
				obj_data += "\n"
				for v in filtered_vertices:
					vt = v[2][:]
					vt[1] = str(1-float(vt[1]))
					obj_data += "vt "+" ".join(vt)+"\n"
				obj_data += "\n"
				for i in range(0, len(indices), 3):
					obj_data += "f {0}/{0}/{0} {1}/{1}/{1} {2}/{2}/{2} \n".format(int(indices[i])+index_offset, int(indices[i+1])+index_offset, int(indices[i+2])+index_offset)
				obj_data += "\n"

				index_offset += len(vertices)
	
	#-----------------------------
			
	mtl_data += OBJ_FIRST_LINE+"\n"
	mtl_data += "\n"

	for shader in shaders:

		mtl_data += "newmtl %s\n" % shader["name"]

		if shader["textures"]["diffuse"] is not None:
			#mtl_data += "map_Ka %s\n" % shader["textures"]["diffuse"]
			mtl_data += "map_Kd %s\n" % shader["textures"]["diffuse"]
			#mtl_data += "map_Ks %s\n" % shader["textures"]["diffuse"]

		if shader["textures"]["bump"] is not None:
			#mtl_data += "bump %s\n" % shader["textures"]["bump"]
			#mtl_data += "norm %s\n" % shader["textures"]["bump"]
			mtl_data += "map_bump %s\n" % shader["textures"]["bump"]

		if shader["textures"]["spec"] is not None:
			mtl_data += "map_Ks %s\n" % shader["textures"]["spec"]

		mtl_data += "\n"

	savefile(obj_path, obj_data)
	savefile(mtl_path, mtl_data)

	times.append(time.time())

	print("Created %s, %s (%.2f s)" % (obj_path, mtl_path, times[-1] - times[0]))

	os.chdir(owd)

def readfile(path):
	with open(path, "r") as file:
		return file.read()

def savefile(path, text):
	with open(path, "w") as file:
		file.write(text)

sys.stdout = Logger()

shader_manager_path = os.path.join(os.path.dirname(__file__), "ShaderManager.xml")
shader_manager_xml = ET.fromstring(readfile(shader_manager_path))

parser = argparse.ArgumentParser()

parser.add_argument("glob", default="*.odr", nargs="?", help="A pattern or name")
parser.add_argument("--force", "-f", default=False, action="store_true", help="Force the converter to reconvert converted files")

args = parser.parse_args()

# if os.path.isdir(odr_path):
# 	paths = os.listdir(odr_path)
# 	odr_paths = [os.path.join(odr_path, p) for p in paths]
# 	odr_paths = [p for p in odr_paths if os.path.isfile(p) and os.path.splitext(p)[1] == ".odr"]
# else:
# 	odr_paths = [odr_path]

odr_paths = glob2.glob(args.glob)

if len(odr_paths) == 0:
	print("No files matching glob found")
else:
	for p in odr_paths:
		parse_odr(p, args.force)
		print("---------------------------------------------")