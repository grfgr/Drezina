// Общие константы мода Drezina.

class DrezinaRPC
{
	// сервер -> клиент
	static const int TRACKS_FULL     = 8817001; // полный список трасс (при входе)
	static const int TRACK_ADD       = 8817002; // добавлена/обновлена трасса
	static const int TRACK_REMOVE    = 8817003; // удалена трасса
	// клиент -> сервер
	static const int ADMIN_COMMAND   = 8817010; // текст команды "/rail ..."
	static const int HC_THROTTLE     = 8817020; // -1 тормоз, 0 отпустил, 1 качаю
	static const int HC_REVERSE      = 8817021; // сменить направление
	static const int HC_LEAVE        = 8817022; // сойти с дрезины
	// сервер -> клиент: метро (для карты КПК)
	static const int TUNNELS_FULL    = 8817004;
	static const int CHAT_MSG        = 8817005; // сообщение мода в чат игрока
}

class DrezinaConst
{
	static const string PROFILE_DIR    = "$profile:Drezina";
	static const string TRACKS_FILE    = "$profile:Drezina/tracks.json";
	static const string SETTINGS_FILE  = "$profile:Drezina/settings.json";
	static const string ADMINS_FILE    = "$profile:Drezina/admins.json";

	static const string CHAT_PREFIX    = "/rail";
	static const string METRO_PREFIX   = "/metro";
	static const string TUNNELS_FILE   = "$profile:Drezina/tunnels.json";

	// Метро: размеры моделей (должны совпадать с tools/blender/make_models.py)
	static const float  TUNNEL_PIECE_LEN  = 10.0; // Drezina_Tunnel10
	static const float  STATION_LEN       = 24.0; // Drezina_MetroStation (по ходу)
	static const float  STATION_BACK      = 4.0;  // сколько станции «за» точкой входа
	static const float  RAIL_TOP_ABOVE_FLOOR = 0.39; // головка рельса над полом: Р65 0.18 + подкладка 0.02 + шпала 0.19
	// бункер: коридор от станции к лестнице и лестничная шахта (см. tools/blender/metro_bunker.py)
	static const float  CORRIDOR_LEN      = 8.0;
	static const float  STAIR_HALF_Y      = 3.0;  // полудлина шахты изнутри
	static const float  BUNKER_WALL       = 0.35;
	static const float  STAIR_TOP         = 9.6;  // высота верхней площадки над полом станции
	static const float  BUNKER_SIDE_X     = -3.0; // проход в коридор: X станции (влево от пути, если смотреть в тоннель)
	static const float  LAMP_STEP         = 30.0; // светильники в тоннеле через 30 м
	static const float  TUNNEL_SHORT_STEP = 2.0;  // шаг коротких звеньев на поворотах (модель 2.4 м, с нахлёстом)
	static const float  METRO_MIN_LEN     = 50.0;

	static const float  RAIL_PIECE_LEN = 2.0;   // длина модели Drezina_Rail
	static const float  SPLINE_STEP    = 1.0;   // шаг сглаженной линии пути, м

	// Если игрок сразу «слетает» с дрезины после посадки — поменяйте на false.
	// (значение, которое HumanCommandScript.PostPhysUpdate должен вернуть, чтобы команда продолжалась)
	static const bool   POSTPHYS_CONTINUE = true;
}

// Настройки сервера ($profile:Drezina/settings.json). Создаются с дефолтами при первом запуске.
class DrezinaSettings
{
	float MaxSpeed            = 9.0;   // м/с (~32 км/ч)
	float PumpAcceleration    = 1.3;   // м/с^2 пока игрок качает (W)
	float BrakeDeceleration   = 4.0;   // м/с^2 при торможении (S)
	float RollingFriction     = 0.25;  // м/с^2 накатом
	float SlopeFactor         = 4.0;   // насколько уклон разгоняет/тормозит
	float ReverseMaxSpeed     = 0.4;   // реверс разрешён только почти на месте
	float DispenserSideOffset = 2.2;   // насколько в сторону от пути стоит станция выдачи
	float DispenserBackOffset = 1.0;   // насколько станция отодвинута от торца пути внутрь
	float HandcarClearance    = 4.5;   // минимальная дистанция между дрезинами на одном пути
	float AbandonSeconds      = 300;   // брошенная дрезина без водителя удаляется через N сек
	int   MaxHandcarsPerTrack = 4;
	float RailHeightOffset    = 0.39;  // подъём головки рельса над точкой, где стоял админ (шпалы ложатся на землю)
	float AutoNodeMinStep     = 2.0;   // минимальный шаг для режима "/rail auto"
	float MetroDefaultDepth   = 20.0;  // пол тоннеля ниже самой низкой точки рельефа над трассой
	float MetroMinFloorY      = 3.0;   // пол не ниже уровня моря + 3 м (иначе игрок «поплывёт»)
	// Локация за картой для метро, которое нельзя спрятать под рельефом (берег, низины).
	// По умолчанию — над морем восточнее Черноруси (карта 15360 x 15360), на высоте 600 м.
	float MetroZoneX          = 17500;
	float MetroZoneZ          = 500;
	float MetroZoneY          = 600;
	float MetroZoneGap        = 150;   // зазор между тоннелями в локации
	string MetroGeneratorType = "PowerGenerator"; // генератор на станции: заправить, вставить свечу, включить
	float MetroPowerCheck     = 2.0;   // как часто проверять генераторы, сек

	static ref DrezinaSettings s_Instance;

	static DrezinaSettings Get()
	{
		if (!s_Instance)
			s_Instance = new DrezinaSettings();
		return s_Instance;
	}

	static void Load()
	{
		s_Instance = new DrezinaSettings();
		if (!FileExist(DrezinaConst.PROFILE_DIR))
			MakeDirectory(DrezinaConst.PROFILE_DIR);

		if (FileExist(DrezinaConst.SETTINGS_FILE))
			JsonFileLoader<DrezinaSettings>.JsonLoadFile(DrezinaConst.SETTINGS_FILE, s_Instance);
		else
			JsonFileLoader<DrezinaSettings>.JsonSaveFile(DrezinaConst.SETTINGS_FILE, s_Instance);
	}
}

// Список админов ($profile:Drezina/admins.json): Steam64 ID.
class DrezinaAdmins
{
	ref array<string> Admins = new array<string>;

	static ref DrezinaAdmins s_Instance;

	static void Load()
	{
		s_Instance = new DrezinaAdmins();
		if (!FileExist(DrezinaConst.PROFILE_DIR))
			MakeDirectory(DrezinaConst.PROFILE_DIR);

		if (FileExist(DrezinaConst.ADMINS_FILE))
		{
			JsonFileLoader<DrezinaAdmins>.JsonLoadFile(DrezinaConst.ADMINS_FILE, s_Instance);
		}
		else
		{
			s_Instance.Admins.Insert("76561190000000000");
			JsonFileLoader<DrezinaAdmins>.JsonSaveFile(DrezinaConst.ADMINS_FILE, s_Instance);
		}
	}

	static bool IsAdmin(PlayerIdentity identity)
	{
		if (!identity)
			return false;
		if (!s_Instance)
			Load();
		return s_Instance.Admins.Find(identity.GetPlainId()) != -1;
	}
}
