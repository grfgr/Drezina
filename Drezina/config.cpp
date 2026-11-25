class CfgPatches
{
	class Drezina
	{
		units[] = {"Drezina_Handcar", "Drezina_Dispenser", "Drezina_Rail"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts"};
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
};
