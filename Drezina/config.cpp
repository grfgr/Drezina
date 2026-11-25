class CfgPatches
{
	class Drezina
	{
		units[] = {"Drezina_Handcar", "Drezina_Dispenser", "Drezina_Rail", "Drezina_Rail10", "Drezina_Tunnel10", "Drezina_Tunnel2", "Drezina_MetroStation", "Drezina_MetroHatch", "Drezina_MetroLadder", "Drezina_TunnelLamp"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts", "DZ_Sounds_Effects"};
	};
};

class CfgMods
{
	class Drezina
	{
		dir = "Drezina";
		name = "Drezina - rails & hand car";
		author = "grfgr";
		type = "mod";
		dependencies[] = {"Game", "World", "Mission"};

		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"Drezina/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"Drezina/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"Drezina/scripts/5_Mission"};
			};
		};
	};
};

// ------------------------------------------------------------------ звуки
// samples[] — пути без расширения (.ogg). Несколько сэмплов в шейдере выбираются случайно.
class CfgSoundShaders
{
	class Drezina_Roll_SoundShader
	{
		samples[] = {{"Drezina\sounds\roll_loop", 1}};
		volume = 1.0;
		range = 70;
	};
	class Drezina_Clack_SoundShader
	{
		samples[] = {{"Drezina\sounds\clack_1", 1}, {"Drezina\sounds\clack_2", 1}, {"Drezina\sounds\clack_3", 1}};
		volume = 1.0;
		range = 90;
	};
	class Drezina_Creak_SoundShader
	{
		samples[] = {{"Drezina\sounds\creak_1", 1}, {"Drezina\sounds\creak_2", 1}, {"Drezina\sounds\creak_3", 1}, {"Drezina\sounds\creak_4", 1}};
		volume = 0.8;
		range = 35;
	};
	class Drezina_Knock_SoundShader
	{
		samples[] = {{"Drezina\sounds\knock_1", 1}, {"Drezina\sounds\knock_2", 1}};
		volume = 0.7;
		range = 30;
	};
	class Drezina_Brake_SoundShader
	{
		samples[] = {{"Drezina\sounds\brake_loop", 1}};
		volume = 0.8;
		range = 80;
	};
};

class CfgSoundSets
{
	class Drezina_Base_SoundSet
	{
		sound3DProcessingType = "character3DProcessingType";
		volumeCurve = "characterAttenuationCurve";
		spatial = 1;
		doppler = 0;
		loop = 0;
	};
	class Drezina_Roll_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Roll_SoundShader"};
		loop = 1;
	};
	class Drezina_Clack_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Clack_SoundShader"};
		loop = 0;
	};
	class Drezina_Creak_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Creak_SoundShader"};
		loop = 0;
	};
	class Drezina_Knock_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Knock_SoundShader"};
		loop = 0;
	};
	class Drezina_Brake_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Brake_SoundShader"};
		loop = 1;
	};
};

class CfgVehicles
{
	class Inventory_Base;
	class HouseNoDestruct;

	// Дрезина (Sheffield hand car, ~1890). Двигается скриптом по рельсам, в инвентарь не берётся.
	class Drezina_Handcar: Inventory_Base
	{
		scope = 2;
		displayName = "Дрезина";
		descriptionShort = "Ручная дрезина Sheffield. Качай рычаг — едешь.";
		model = "\Drezina\data\handcar.p3d";
		weight = 227000;
		itemSize[] = {10, 10};
		itemBehaviour = 0;
		carveNavmesh = 0;
		physLayer = "item_large";
		rotationFlags = 0;

		class AnimationSources
		{
			// Качающийся рычаг (коромысло). 0 = одна ручка внизу, 1 = другая.
			class drezina_lever
			{
				source = "user";
				animPeriod = 0.001;
				initPhase = 0.5;
			};
			// Вращение колёс, фаза 0..1 = один оборот.
			class drezina_wheels
			{
				source = "user";
				animPeriod = 0.001;
				initPhase = 0;
			};
		};
	};

	// Будка/стойка выдачи дрезин у концов путей.
	class Drezina_Dispenser: HouseNoDestruct
	{
		scope = 1;
		displayName = "Станция выдачи дрезин";
		model = "\Drezina\data\dispenser.p3d";
	};

	// Звено пути длиной 2 м (два рельса + шпалы). Ставится сервером по точкам трассы.
	class Drezina_Rail: HouseNoDestruct
	{
		scope = 1;
		displayName = "Рельсы";
		model = "\Drezina\data\rail_2m.p3d";
	};

	// Прямое звено пути 10 м (на прямых участках вместо пяти по 2 м).
	class Drezina_Rail10: HouseNoDestruct
	{
		scope = 1;
		displayName = "Рельсы";
		model = "\Drezina\data\rail_10m.p3d";
	};

	// ---------------------------------------------------------------- метро

	// Звено тоннеля 10 м: пол, стены, свод. Origin на уровне пола по центру.
	class Drezina_Tunnel10: HouseNoDestruct
	{
		scope = 1;
		displayName = "Тоннель";
		model = "\Drezina\data\tunnel_10m.p3d";
	};

	// Короткое звено тоннеля для поворотов: 2.4 м, ставится через 2 м (с нахлёстом, чтобы не было щелей).
	class Drezina_Tunnel2: HouseNoDestruct
	{
		scope = 1;
		displayName = "Тоннель";
		model = "\Drezina\data\tunnel_2m.p3d";
	};

	// Подземная станция 24 x 12 м, один торец глухой, другой открыт в тоннель.
	class Drezina_MetroStation: HouseNoDestruct
	{
		scope = 1;
		displayName = "Станция метро";
		model = "\Drezina\data\metro_station.p3d";
	};

	// Павильон-спуск на поверхности.
	class Drezina_MetroHatch: HouseNoDestruct
	{
		scope = 1;
		displayName = "Вход в метро";
		model = "\Drezina\data\metro_hatch.p3d";
	};

	// Лестница наверх на станции.
	class Drezina_MetroLadder: HouseNoDestruct
	{
		scope = 1;
		displayName = "Выход наверх";
		model = "\Drezina\data\metro_ladder.p3d";
	};

	// Светильник под сводом (свет создаётся скриптом на клиенте).
	class Drezina_TunnelLamp: HouseNoDestruct
	{
		scope = 1;
		displayName = "Светильник";
		model = "\Drezina\data\tunnel_lamp.p3d";
	};
};
