class CfgPatches
{
	class Drezina
	{
		units[] = {"Drezina_Motor", "Drezina_TrailerPassenger", "Drezina_TrailerCargo", "Drezina_TrailerBarrel", "Drezina_Handcar", "Drezina_Dispenser", "Drezina_Rail", "Drezina_Rail1", "Drezina_Rail10", "Drezina_Tunnel10", "Drezina_Tunnel10Tile", "Drezina_Tunnel10B", "Drezina_Tunnel10C", "Drezina_Tunnel10D", "Drezina_Tunnel10E", "Drezina_Tunnel10F", "Drezina_Tunnel10G", "Drezina_Tunnel2", "Drezina_JunctionHall", "Drezina_JunctionWall", "Drezina_JunctionPortal", "Drezina_MetroStation", "Drezina_MetroHatch", "Drezina_MetroLadder", "Drezina_BunkerStairs", "Drezina_BunkerCorridor", "Drezina_TunnelLamp", "Drezina_AlarmLamp"};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Scripts", "DZ_Sounds_Effects", "DZ_Vehicles_Wheeled", "DZ_Vehicles_Singletrack"};
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
		// другие моды (например, КПК) могут проверять наличие метро через #ifdef DREZINA
		defines[] = {"DREZINA"};
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
	class Drezina_Door_SoundShader
	{
		samples[] = {{"\DZ\sounds\environment\buildings\doors\MetalValve\doorMetalValveOpen_1", 1}, {"\DZ\sounds\environment\buildings\doors\MetalValve\doorMetalValveOpen_2", 1}};
		volume = 1.0;
		range = 40;
	};
	class Drezina_Dynamo_SoundShader
	{
		samples[] = {{"Drezina\sounds\dynamo_loop", 1}};
		volume = 0.6;
		range = 25;
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
	class Drezina_Door_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Door_SoundShader"};
		loop = 0;
	};
	class Drezina_Dynamo_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Dynamo_SoundShader"};
		loop = 1;
	};
	class Drezina_Brake_SoundSet: Drezina_Base_SoundSet
	{
		soundShaders[] = {"Drezina_Brake_SoundShader"};
		loop = 1;
	};
};

// слоты бочек грузового прицепа (каждая бочка — отдельное хранилище)
class CfgSlots
{
	class Slot_DrezinaBarrel1
	{
		name = "DrezinaBarrel1";
		displayName = "Бочка 1";
		ghostIcon = "set:dayz_inventory image:cat_common_cargo";
	};
	class Slot_DrezinaBarrel2: Slot_DrezinaBarrel1
	{
		name = "DrezinaBarrel2";
		displayName = "Бочка 2";
	};
	class Slot_DrezinaBarrel3: Slot_DrezinaBarrel1
	{
		name = "DrezinaBarrel3";
		displayName = "Бочка 3";
	};
	class Slot_DrezinaBarrel4: Slot_DrezinaBarrel1
	{
		name = "DrezinaBarrel4";
		displayName = "Бочка 4";
	};
};

class CfgVehicles
{
	class Inventory_Base;
	class Container_Base;
	class HouseNoDestruct;

	// Дрезина (Sheffield hand car, ~1890). Двигается скриптом по рельсам, в инвентарь не берётся.
	// ------------------------------------------------------------------ мотодрезина (машина DayZ)
	// Садятся как в машину: водитель + 2 пассажира (сзади по бортам, ногами наружу).
	// Мотор от мотоцикла: нужен бензин, свеча и аккумулятор, фары — лампочки H7.
	// Колёс-запчастей нет: по рельсам машину ведёт скрипт (Drezina_Motor.c).
	class Car;
	class CarScript: Car
	{
		class AnimationSources;
	};
	class Drezina_Motor: CarScript
	{
		scope = 2;
		displayName = "Мотодрезина";
		descriptionShort = "Дрезина с мотоциклетным мотором. Заправь, вставь свечу и аккумулятор — и по рельсам.";
		model = "\Drezina\data\motor_handcar.p3d";
		attachments[] = {"SparkPlug", "Reflector_1_1", "Reflector_2_1", "NivaWheel_1_1", "NivaWheel_1_2", "NivaWheel_2_1", "NivaWheel_2_2"};
		hiddenSelections[] = {"light_left", "light_right", "light_brake_1_2", "light_brake_2_2", "light_reverse_1_2", "light_reverse_2_2", "light_1_2", "light_2_2", "light_dashboard"};
		// свои стёкла фар: мутно-белое (спереди) и красное (стоп сзади); _e — светящийся вариант
		hiddenSelectionsTextures[] = {"Drezina\data\textures\drezina_glass_co.paa", "Drezina\data\textures\drezina_glass_co.paa", "Drezina\data\textures\drezina_redglass_co.paa", "", "", "", "", "", ""};
		hiddenSelectionsMaterials[] = {"Drezina\data\textures\drezina_glass.rvmat", "Drezina\data\textures\drezina_glass.rvmat", "Drezina\data\textures\drezina_redglass.rvmat", "", "", "", "", "", ""};
		frontReflectorMatOn = "Drezina\data\textures\drezina_glass_e.rvmat";
		frontReflectorMatOff = "Drezina\data\textures\drezina_glass.rvmat";
		brakeReflectorMatOn = "Drezina\data\textures\drezina_redglass_e.rvmat";
		brakeReflectorMatOff = "Drezina\data\textures\drezina_redglass.rvmat";
		ReverseReflectorMatOn = "Drezina\data\textures\drezina_glass_e.rvmat";
		ReverseReflectorMatOff = "Drezina\data\textures\drezina_glass.rvmat";
		TailReflectorMatOn = "Drezina\data\textures\drezina_redglass_e.rvmat";
		TailReflectorMatOff = "Drezina\data\textures\drezina_redglass.rvmat";
		dashboardMatOn = "Drezina\data\textures\drezina_glass.rvmat";
		dashboardMatOff = "Drezina\data\textures\drezina_glass.rvmat";
		fuelCapacity = 20;
		fuelConsumption = 3;

		class Crew
		{
			class Driver
			{
				actionSel = "seat_driver";
				proxyPos = "crewDriver";
				getInPos = "pos_driver";
				getInDir = "pos_driver_dir";
				isDriver = 1;
			};
			class Cargo1
			{
				actionSel = "seat_cargo1";
				proxyPos = "crewCargo1";
				getInPos = "pos_cargo1";
				getInDir = "pos_cargo1_dir";
			};
			class Cargo2
			{
				actionSel = "seat_cargo2";
				proxyPos = "crewCargo2";
				getInPos = "pos_cargo2";
				getInDir = "pos_cargo2_dir";
			};
		};

		class SimulationModule
		{
			class Steering
			{
				maxSteeringAngle = 1;
				increaseSpeed[] = {0, 10};
				decreaseSpeed[] = {0, 10};
				centeringSpeed[] = {0, 10};
			};
			class Throttle
			{
				reactionTime = 0.5;
				defaultThrust = 0.85;
				gentleThrust = 0.4;
				turboCoef = 2;
				gentleCoef = 0.75;
			};
			class Brake
			{
				pressureBySpeed[] = {0, 0.5, 40, 0.5};
				reactionTime = 0.3;
				driverless = 0.5;
			};
			class Aerodynamics
			{
				frontalArea = 1.5;
				dragCoefficient = 0.8;
			};
			drive = "DRIVE_RWD";
			class Engine
			{
				torqueCurve[] = {400, 0, 1100, 6, 2500, 10, 4500, 12, 5500, 10, 6000, 7, 7000, 0};
				inertia = 0.04;
				frictionTorque = 1;
				rollingFriction = 0.1;
				viscousFriction = 0.5;
				rpmIdle = 1200;
				rpmMin = 1400;
				rpmClutch = 1500;
				rpmRedline = 6000;
			};
			class Clutch
			{
				maxTorqueTransfer = 40;
				uncoupleTime = 0.2;
				coupleTime = 0.5;
			};
			class Gearbox
			{
				type = "GEARBOX_MANUAL";
				reverse = 3.0;
				ratios[] = {2.4};
			};
			class Axles
			{
				class Front
				{
					maxBrakeTorque = 800;
					maxHandbrakeTorque = 1500;
					wheelHubMass = 10;
					wheelHubRadius = 0.36;
					class Differential
					{
						ratio = 4.0;
						type = "DIFFERENTIAL_LOCKED";
					};
					class Suspension
					{
						stiffness = 30000;
						compression = 2000;
						damping = 6000;
						travelMaxUp = 0.02;
						travelMaxDown = 0.02;
					};
					class Wheels
					{
						class Left
						{
							inventorySlot = "NivaWheel_1_1";
							animTurn = "turnfrontleft";
							animRotation = "wheelfrontleft";
							animDamper = "";
							wheelHub = "wheel_1_1_damper_land";
						};
						class Right
						{
							inventorySlot = "NivaWheel_2_1";
							animTurn = "turnfrontright";
							animRotation = "wheelfrontright";
							animDamper = "";
							wheelHub = "wheel_2_1_damper_land";
						};
					};
				};
				class Rear
				{
					maxBrakeTorque = 800;
					maxHandbrakeTorque = 1500;
					wheelHubMass = 10;
					wheelHubRadius = 0.36;
					class Differential
					{
						ratio = 4.0;
						type = "DIFFERENTIAL_LOCKED";
					};
					class Suspension
					{
						stiffness = 30000;
						compression = 2000;
						damping = 6000;
						travelMaxUp = 0.02;
						travelMaxDown = 0.02;
					};
					class Wheels
					{
						class Left
						{
							inventorySlot = "NivaWheel_1_2";
							animTurn = "turnbackleft";
							animRotation = "wheelbackleft";
							animDamper = "";
							wheelHub = "wheel_1_2_damper_land";
						};
						class Right
						{
							inventorySlot = "NivaWheel_2_2";
							animTurn = "turnbackright";
							animRotation = "wheelbackright";
							animDamper = "";
							wheelHub = "wheel_2_2_damper_land";
						};
					};
				};
			};
		};

		// сумка напротив водителя: чуть больше деревянного ящика
		class Cargo
		{
			itemsCargoSize[] = {10, 6};
			allowOwnedCargoManipulation = 1;
			openable = 0;
		};

		class AnimationSources: AnimationSources
		{
			class drezina_wheels
			{
				source = "user";
				animPeriod = 0.001;
				initPhase = 0;
			};
		};

		// звук мотора — ванильный мотоцикл (Motorbike_01)
		class Sounds
		{
			thrust = 0.6;
			thrustTurbo = 1;
			thrustGentle = 0.3;
			thrustSmoothCoef = 0.02;
			camposSmoothCoef = 0.03;
			soundSetsFilter[] =
			{
				"Motorbike_01_Engine_Offload_Ext_Rpm1_SoundSet",
				"Motorbike_01_Engine_Offload_Ext_Rpm2_SoundSet",
				"Motorbike_01_Engine_Offload_Ext_Rpm3_SoundSet",
				"Motorbike_01_Engine_Offload_Ext_Rpm4_SoundSet",
				"Motorbike_01_Engine_Offload_Ext_Rpm5_SoundSet",
				"Motorbike_01_Engine_Offload_Ext_Rpm6_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm0_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm1_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm2_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm3_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm4_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm5_SoundSet",
				"Motorbike_01_Engine_Ext_Rpm6_SoundSet",
				"Motorbike_01_Engine_Ext_Broken_SoundSet"
			};
			soundSetsInt[] = {"Motorbike_01_Wind_SoundSet"};
		};

		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 3000;
					healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
				};
			};
			class DamageZones
			{
				class Chassis
				{
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_chassis"};
					class Health
					{
						hitpoints = 3000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
					};
					inventorySlots[] = {};
				};
				class Engine
				{
					fatalInjuryCoef = 0.001;
					memoryPoints[] = {"dmgZone_engine"};
					componentNames[] = {"dmgZone_engine"};
					class Health
					{
						hitpoints = 1000;
						transferToGlobalCoef = 1;
						healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
					};
					inventorySlots[] = {"SparkPlug"};
					inventorySlotsCoefs[] = {0.03};
				};
				class FuelTank
				{
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_fuelTank"};
					class Health
					{
						hitpoints = 600;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
					};
					inventorySlots[] = {};
				};
				class Reflector_1_1
				{
					fatalInjuryCoef = -1;
					memoryPoints[] = {"dmgZone_lights_1_1"};
					componentNames[] = {};
					class Health
					{
						hitpoints = 10;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
					};
					inventorySlots[] = {"Reflector_1_1"};
					inventorySlotsCoefs[] = {1};
				};
				class Reflector_2_1: Reflector_1_1
				{
					memoryPoints[] = {"dmgZone_lights_2_1"};
					inventorySlots[] = {"Reflector_2_1"};
				};
			};
		};

		class GUIInventoryAttachmentsProps
		{
			class Engine
			{
				name = "$STR_attachment_Engine0";
				description = "";
				icon = "set:dayz_inventory image:cat_vehicle_engine";
				attachmentSlots[] = {"SparkPlug"};
			};
			class Body
			{
				name = "$STR_attachment_Body0";
				description = "";
				icon = "set:dayz_inventory image:cat_vehicle_body";
				attachmentSlots[] = {"Reflector_1_1", "Reflector_2_1"};
			};
		};
	};


	// ------------------------------------------------------------------ прицепы к мотодрезине
	// Машина без водителя: ходовая (SimulationModule), звук и материалы фонарей — от мотодрезины.
	class Drezina_TrailerBase: Drezina_Motor
	{
		scope = 0;
		displayName = "Прицеп мотодрезины";
		descriptionShort = "Цепляется к мотодрезине у терминала выдачи.";
		attachments[] = {"NivaWheel_1_1", "NivaWheel_1_2", "NivaWheel_2_1", "NivaWheel_2_2"};
		fuelCapacity = 1;
		class Crew {};
		class Cargo
		{
			itemsCargoSize[] = {0, 0};
			openable = 0;
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 3000;
					healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
				};
			};
			class DamageZones
			{
				class Chassis
				{
					fatalInjuryCoef = -1;
					componentNames[] = {"dmgZone_chassis"};
					class Health
					{
						hitpoints = 3000;
						transferToGlobalCoef = 0;
						healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
					};
					inventorySlots[] = {};
				};
			};
		};
		class GUIInventoryAttachmentsProps {};
	};

	// пассажирский: две лавки спинками друг к другу, 4 места лицом в стороны
	class Drezina_TrailerPassenger: Drezina_TrailerBase
	{
		scope = 2;
		displayName = "Пассажирский прицеп";
		model = "\Drezina\data\trailer_passenger.p3d";
		class Crew
		{
			class Cargo1
			{
				actionSel = "seat_cargo1";
				proxyPos = "crewCargo1";
				getInPos = "pos_cargo1";
				getInDir = "pos_cargo1_dir";
			};
			class Cargo2
			{
				actionSel = "seat_cargo2";
				proxyPos = "crewCargo2";
				getInPos = "pos_cargo2";
				getInDir = "pos_cargo2_dir";
			};
			class Cargo3
			{
				actionSel = "seat_cargo3";
				proxyPos = "crewCargo3";
				getInPos = "pos_cargo3";
				getInDir = "pos_cargo3_dir";
			};
			class Cargo4
			{
				actionSel = "seat_cargo4";
				proxyPos = "crewCargo4";
				getInPos = "pos_cargo4";
				getInDir = "pos_cargo4_dir";
			};
		};
	};

	// грузовой: 4 бочки, каждая — своё хранилище
	class Drezina_TrailerCargo: Drezina_TrailerBase
	{
		scope = 2;
		displayName = "Грузовой прицеп";
		model = "\Drezina\data\trailer_cargo.p3d";
		attachments[] = {"NivaWheel_1_1", "NivaWheel_1_2", "NivaWheel_2_1", "NivaWheel_2_2", "DrezinaBarrel1", "DrezinaBarrel2", "DrezinaBarrel3", "DrezinaBarrel4"};
		class GUIInventoryAttachmentsProps
		{
			class Barrels
			{
				name = "Бочки";
				description = "";
				icon = "set:dayz_inventory image:cat_common_cargo";
				attachmentSlots[] = {"DrezinaBarrel1", "DrezinaBarrel2", "DrezinaBarrel3", "DrezinaBarrel4"};
			};
		};
	};

	class Drezina_TrailerBarrel: Container_Base
	{
		scope = 2;
		displayName = "Бочка прицепа";
		descriptionShort = "Бочка на грузовом прицепе мотодрезины.";
		model = "\Drezina\data\trailer_barrel.p3d";
		weight = 10000;
		itemSize[] = {10, 10};
		itemBehaviour = 0;
		inventorySlot[] = {"DrezinaBarrel1", "DrezinaBarrel2", "DrezinaBarrel3", "DrezinaBarrel4"};
		carveNavmesh = 0;
		canBeDigged = 0;
		class Cargo
		{
			itemsCargoSize[] = {10, 10};
			openable = 0;
			allowOwnedCargoManipulation = 1;
		};
		class DamageSystem
		{
			class GlobalHealth
			{
				class Health
				{
					hitpoints = 1000;
					healthLevels[] = {{1, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0, {}}};
				};
			};
		};
	};

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
	// звено 1 м: на кривых и съездах развязок (плавнее, без изломов)
	class Drezina_Rail1: HouseNoDestruct
	{
		scope = 1;
		displayName = "Рельсы";
		model = "\Drezina\data\rail_1m.p3d";
	};
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

	// звено у станции: стены в кафеле (дальше по тоннелю — кирпич)
	class Drezina_Tunnel10Tile: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_tile.p3d";
	};
	// (старые варианты звена; сейчас не используются)
	class Drezina_Tunnel10B: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_b.p3d";
	};
	class Drezina_Tunnel10C: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_c.p3d";
	};
	class Drezina_Tunnel10D: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_d.p3d";
	};
	// ещё три: служебная ниша с ТП (E), брошенный блокпост (F), аварийная деревянная крепь (G)
	class Drezina_Tunnel10E: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_e.p3d";
	};
	class Drezina_Tunnel10F: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_f.p3d";
	};
	class Drezina_Tunnel10G: Drezina_Tunnel10
	{
		model = "\Drezina\data\tunnel_10m_g.p3d";
	};

	// Короткое звено тоннеля для поворотов: 2.4 м, ставится через 2 м (с нахлёстом, чтобы не было щелей).
	class Drezina_Tunnel2: HouseNoDestruct
	{
		scope = 1;
		displayName = "Тоннель";
		model = "\Drezina\data\tunnel_2m.p3d";
	};

	// Зал развязки на пересечении линий метро: круг R=24 м; стены — панелями, у тоннелей — порталы.
	class Drezina_JunctionHall: HouseNoDestruct
	{
		scope = 1;
		displayName = "Развязка метро";
		model = "\Drezina\data\junction_hall.p3d";
	};
	class Drezina_JunctionWall: HouseNoDestruct
	{
		scope = 1;
		displayName = "Стена";
		model = "\Drezina\data\junction_wall.p3d";
	};
	class Drezina_JunctionPortal: HouseNoDestruct
	{
		scope = 1;
		displayName = "Портал тоннеля";
		model = "\Drezina\data\junction_portal.p3d";
	};

	// Подземная станция 24 x 12 м, один торец глухой, другой открыт в тоннель.
	class Drezina_MetroStation: HouseNoDestruct
	{
		scope = 1;
		displayName = "Станция метро";
		model = "\Drezina\data\metro_station.p3d";
	};

	// Голова бункера на поверхности: бетонный блок в насыпи, гермодверь в жёлто-чёрной коробке.
	class Drezina_MetroHatch: HouseNoDestruct
	{
		scope = 1;
		displayName = "Вход в бункер";
		model = "\Drezina\data\bunker_entrance.p3d";
	};

	// Гермодверь изнутри, на верхней площадке лестницы.
	class Drezina_MetroLadder: HouseNoDestruct
	{
		scope = 1;
		displayName = "Выход наружу";
		model = "\Drezina\data\bunker_inner_door.p3d";
	};

	// Лестничная шахта: 4 марша вниз, 9.6 м.
	class Drezina_BunkerStairs: HouseNoDestruct
	{
		scope = 1;
		displayName = "Лестница";
		model = "\Drezina\data\bunker_stairs.p3d";
	};

	// Коридор от лестницы к станции, 8 м.
	class Drezina_BunkerCorridor: HouseNoDestruct
	{
		scope = 1;
		displayName = "Коридор";
		model = "\Drezina\data\bunker_corridor.p3d";
	};

	// Светильник метро (горит от генератора станции). Item, чтобы синхронизировать вкл/выкл.
	// аварийный красный маячок (горит всегда, луч вращается)
	class Drezina_AlarmLamp: Inventory_Base
	{
		scope = 2;
		displayName = "Аварийный маячок";
		model = "\Drezina\data\alarm_lamp.p3d";
		weight = 2000;
		itemSize[] = {2, 2};
		carveNavmesh = 0;
	};
	class Drezina_TunnelLamp: Inventory_Base
	{
		scope = 2;
		displayName = "Светильник";
		model = "\Drezina\data\tunnel_lamp.p3d";
		hiddenSelections[] = {"glass"};
		hiddenSelectionsTextures[] = {"Drezina\data\textures\drezina_glass_co.paa"};
		hiddenSelectionsMaterials[] = {"Drezina\data\textures\drezina_glass.rvmat"};
		weight = 2000;
		itemSize[] = {2, 2};
		carveNavmesh = 0;
	};
};
