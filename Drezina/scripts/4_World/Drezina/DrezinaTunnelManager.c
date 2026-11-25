// Метро: подземный тоннель с двумя станциями, люками-спусками на поверхности и рельсами внутри.
//
// В рельефе DayZ нельзя сделать дыру, поэтому в метро попадают через павильон-люк:
// действие «Спуститься в метро» переносит игрока на подземную станцию прямо под люком,
// лестница на станции — обратно наверх.
//
// Админ: стоит в точке входа A -> "/metro a", идёт/телепортируется к точке B -> "/metro b",
// затем "/metro build [глубина]". Тоннель прямой, пол горизонтальный, ниже самой низкой точки рельефа
// над трассой на заданную глубину.

class DrezinaMetroDraft
{
	vector A;
	vector B;
	bool HasA;
	bool HasB;
}

class DrezinaTunnelManager
{
	// Готовая раскладка для Черноруси (координаты карты X, Z — примерные, около окраин посёлков):
	// вход A — восточная окраина Старого Собора, вход B — южная окраина Выбора. ~2.3 км по прямой,
	// всё время по высокому плато (~250-300 м), так что пол на глубине 20 м далеко от уровня моря.
	static const float PRESET_AX = 5900;
	static const float PRESET_AZ = 7800;
	static const float PRESET_BX = 3800;
	static const float PRESET_BZ = 8700;

	static ref DrezinaTunnelManager s_Instance;

	ref map<int, ref DrezinaTunnelData> m_Tunnels = new map<int, ref DrezinaTunnelData>;
	ref map<int, ref array<Object>> m_Objects = new map<int, ref array<Object>>;
	ref map<string, ref DrezinaMetroDraft> m_Drafts = new map<string, ref DrezinaMetroDraft>;

	static DrezinaTunnelManager Get()
	{
		if (!s_Instance)
			s_Instance = new DrezinaTunnelManager();
		return s_Instance;
	}

	// ------------------------------------------------------------------ загрузка / сохранение

	void ServerInit()
	{
		DrezinaTunnelsDB db = new DrezinaTunnelsDB();
		if (FileExist(DrezinaConst.TUNNELS_FILE))
			JsonFileLoader<DrezinaTunnelsDB>.JsonLoadFile(DrezinaConst.TUNNELS_FILE, db);
		foreach (DrezinaTunnelData t : db.Tunnels)
		{
			if (!t)
				continue;
			m_Tunnels.Set(t.Id, t);
			SpawnTunnel(t);
		}
		Print("[Drezina] loaded tunnels: " + m_Tunnels.Count());
	}

	void Save()
	{
		if (!FileExist(DrezinaConst.PROFILE_DIR))
			MakeDirectory(DrezinaConst.PROFILE_DIR);
		DrezinaTunnelsDB db = new DrezinaTunnelsDB();
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
			db.Tunnels.Insert(t);
		JsonFileLoader<DrezinaTunnelsDB>.JsonSaveFile(DrezinaConst.TUNNELS_FILE, db);
	}

	int NextId()
	{
		int maxId = 0;
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			if (id > maxId)
				maxId = id;
		}
		return maxId + 1;
	}

	// ------------------------------------------------------------------ геометрия

	static vector FlatDir(DrezinaTunnelData t)
	{
		vector d = t.B - t.A;
		d[1] = 0;
		return d.Normalized();
	}

	static vector Side(vector dir)
	{
		return Vector(dir[2], 0, -dir[0]);
	}

	static vector Under(DrezinaTunnelData t, vector surface)
	{
		return Vector(surface[0], t.FloorY, surface[2]);
	}

	static float FlatDistance(vector a, vector b)
	{
		a[1] = 0;
		b[1] = 0;
		return vector.Distance(a, b);
	}

	// Самая низкая точка рельефа над трассой (с запасом по ширине тоннеля).
	static float MinSurfaceAlong(vector a, vector b)
	{
		vector dir = b - a;
		dir[1] = 0;
		float len = dir.Length();
		dir.Normalize();
		vector side = Side(dir);
		float minY = 100000;
		float d = -DrezinaConst.STATION_BACK;
		while (d <= len + DrezinaConst.STATION_BACK)
		{
			for (int k = -1; k <= 1; k++)
			{
				vector p = a + dir * d + side * (k * 5.0);
				float y = GetGame().SurfaceY(p[0], p[2]);
				if (y < minY)
					minY = y;
			}
			d += 5.0;
		}
		return minY;
	}

	// Где оказывается игрок после спуска (у лестницы станции) и после подъёма (рядом с люком).
	vector GetStationSpawn(DrezinaTunnelData t, int end)
	{
		vector dir = FlatDir(t);
		vector surf = t.A;
		vector inward = dir;
		if (end == 1)
		{
			surf = t.B;
			inward = dir * -1;
		}
		// станции выдачи стоят справа от пути (+Side(dir)), лестница и точка появления — слева
		return Under(t, surf) - inward * 2.0 - Side(dir) * 3.0 + Vector(0, 0.05, 0);
	}

	vector GetSurfaceSpawn(DrezinaTunnelData t, int end)
	{
		vector dir = FlatDir(t);
		vector surf = t.A;
		if (end == 1)
		{
			surf = t.B;
			dir = dir * -1;
		}
		vector p = surf + dir * 3.0;
		p[1] = GetGame().SurfaceY(p[0], p[2]) + 0.05;
		return p;
	}

	// ------------------------------------------------------------------ спавн

	void SpawnTunnel(DrezinaTunnelData t)
	{
		DespawnTunnel(t.Id);
		array<Object> objs = new array<Object>;

		vector dir = FlatDir(t);
		vector uA = Under(t, t.A);
		vector uB = Under(t, t.B);
		float total = FlatDistance(t.A, t.B);

		// станции (открытый торец смотрит в тоннель)
		float stCenter = DrezinaConst.STATION_LEN * 0.5 - DrezinaConst.STATION_BACK;
		AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_MetroStation", uA + dir * stCenter, dir));
		AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_MetroStation", uB - dir * stCenter, dir * -1));

		// тоннель между станциями
		float tStart = DrezinaConst.STATION_LEN - DrezinaConst.STATION_BACK;
		float tLen = total - tStart * 2;
		float piece = DrezinaConst.TUNNEL_PIECE_LEN;
		if (tLen > 0)
		{
			int pieces = Math.Ceil(tLen / piece);
			for (int i = 0; i < pieces; i++)
			{
				float c = i * piece + piece * 0.5;
				if (c + piece * 0.5 > tLen)
					c = Math.Max(tLen - piece * 0.5, piece * 0.5);
				AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_Tunnel10", uA + dir * (tStart + c), dir));
			}
		}

		// светильники под сводом
		float lampD = 2.0;
		while (lampD < total - 2.0)
		{
			AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_TunnelLamp", uA + dir * lampD + Vector(0, 4.3, 0), dir));
			lampD += DrezinaConst.LAMP_STEP;
		}

		// люки на поверхности и лестницы на станциях
		SpawnEntrance(t, 0, objs);
		SpawnEntrance(t, 1, objs);

		m_Objects.Set(t.Id, objs);

		// путь внутри (создаётся один раз, дальше живёт в tracks.json как обычный путь)
		if (t.TrackId == 0 || !DrezinaTrackManager.Get().GetTrack(t.TrackId))
		{
			array<vector> nodes = new array<vector>;
			vector railUp = Vector(0, DrezinaConst.RAIL_TOP_ABOVE_FLOOR, 0);
			nodes.Insert(uA + dir * 0.5 + railUp);
			nodes.Insert(uB - dir * 0.5 + railUp);
			t.TrackId = DrezinaTrackManager.Get().CreateTrack(nodes, "Метро " + t.Id);
			Save();
		}
	}

	void SpawnEntrance(DrezinaTunnelData t, int end, array<Object> objs)
	{
		vector dir = FlatDir(t);
		vector surf = t.A;
		vector inward = dir;
		if (end == 1)
		{
			surf = t.B;
			inward = dir * -1;
		}

		// павильон на поверхности, вход смотрит по направлению тоннеля
		vector hPos = surf;
		hPos[1] = GetGame().SurfaceY(hPos[0], hPos[2]);
		Drezina_MetroHatch hatch = Drezina_MetroHatch.Cast(DrezinaTrackManager.SpawnStatic("Drezina_MetroHatch", hPos, inward));
		if (hatch)
		{
			hatch.m_TunnelId = t.Id;
			hatch.m_End = end;
			objs.Insert(hatch);
		}

		// лестница у глухой стены станции
		vector lPos = Under(t, surf) - inward * (DrezinaConst.STATION_BACK - 0.6) - Side(dir) * 3.0;
		Drezina_MetroLadder ladder = Drezina_MetroLadder.Cast(DrezinaTrackManager.SpawnStatic("Drezina_MetroLadder", lPos, inward));
		if (ladder)
		{
			ladder.m_TunnelId = t.Id;
			ladder.m_End = end;
			objs.Insert(ladder);
		}
	}

	static void AddObj(array<Object> objs, Object o)
	{
		if (o)
			objs.Insert(o);
	}

	void DespawnTunnel(int id)
	{
		array<Object> objs = m_Objects.Get(id);
		if (objs)
		{
			foreach (Object o : objs)
			{
				if (o)
					GetGame().ObjectDelete(o);
			}
		}
		m_Objects.Remove(id);
	}

	// ------------------------------------------------------------------ телепорт

	void ServerTeleport(PlayerBase player, int tunnelId, int end, bool down)
	{
		DrezinaTunnelData t = m_Tunnels.Get(tunnelId);
		if (!t || !player || !player.IsAlive() || player.m_DrezinaHandcar)
			return;
		vector pos;
		vector look = FlatDir(t);
		if (end == 1)
			look = look * -1;
		if (down)
			pos = GetStationSpawn(t, end);
		else
			pos = GetSurfaceSpawn(t, end);
		player.SetPosition(pos);
		player.SetDirection(look);
	}

	// ------------------------------------------------------------------ команды

	void ServerOnAdminCommand(PlayerIdentity sender, string text)
	{
		if (!DrezinaAdmins.IsAdmin(sender))
		{
			DrezinaTrackManager.Notify(sender, "Нет прав: ваш Steam ID не в admins.json");
			return;
		}
		PlayerBase admin = PlayerBase.Cast(sender.GetPlayer());
		if (!admin)
			return;

		text.TrimInPlace();
		array<string> raw = new array<string>;
		text.Split(" ", raw);
		array<string> args = new array<string>;
		foreach (string a : raw)
		{
			if (a != "")
				args.Insert(a);
		}
		string cmd = "help";
		if (args.Count() >= 2)
			cmd = args[1];
		cmd.ToLower();

		string uid = sender.GetPlainId();
		DrezinaMetroDraft draft = m_Drafts.Get(uid);
		if (!draft)
		{
			draft = new DrezinaMetroDraft();
			m_Drafts.Set(uid, draft);
		}
		vector here = admin.GetPosition();

		if (cmd == "a" || cmd == "b")
		{
			if (cmd == "a")
			{
				draft.A = here;
				draft.HasA = true;
			}
			else
			{
				draft.B = here;
				draft.HasB = true;
			}
			string info = "Точка " + cmd + " запомнена.";
			if (draft.HasA && draft.HasB)
				info += " Расстояние " + Math.Round(FlatDistance(draft.A, draft.B)) + " м. Строить: /metro build";
			DrezinaTrackManager.Notify(sender, info);
		}
		else if (cmd == "info")
		{
			if (!draft.HasA || !draft.HasB)
			{
				DrezinaTrackManager.Notify(sender, "Нужны обе точки: /metro a и /metro b");
				return;
			}
			float minY = MinSurfaceAlong(draft.A, draft.B);
			DrezinaTrackManager.Notify(sender, "Длина " + Math.Round(FlatDistance(draft.A, draft.B)) + " м, минимум рельефа " + Math.Round(minY) + " м, пол будет на " + Math.Round(minY - DrezinaSettings.Get().MetroDefaultDepth) + " м");
		}
		else if (cmd == "build")
		{
			if (!draft.HasA || !draft.HasB)
			{
				DrezinaTrackManager.Notify(sender, "Нужны обе точки: /metro a и /metro b");
				return;
			}
			float dist = FlatDistance(draft.A, draft.B);
			float minLen = (DrezinaConst.STATION_LEN - DrezinaConst.STATION_BACK) * 2 + 10;
			if (dist < minLen)
			{
				DrezinaTrackManager.Notify(sender, "Слишком близко: нужно хотя бы " + minLen + " м между точками.");
				return;
			}
			float depth = DrezinaSettings.Get().MetroDefaultDepth;
			if (args.Count() >= 3)
				depth = Math.Max(args[2].ToFloat(), 8.0);
			float floorY = MinSurfaceAlong(draft.A, draft.B) - depth;
			if (floorY < DrezinaSettings.Get().MetroMinFloorY)
			{
				DrezinaTrackManager.Notify(sender, "Местность слишком низкая (пол ушёл бы ниже моря). Выберите место выше или глубину меньше.");
				return;
			}

			DrezinaTunnelData t = new DrezinaTunnelData();
			t.Id = NextId();
			t.A = draft.A;
			t.B = draft.B;
			t.FloorY = floorY;
			m_Tunnels.Set(t.Id, t);
			SpawnTunnel(t);
			Save();
			m_Drafts.Remove(uid);
			DrezinaTrackManager.Notify(sender, "Метро #" + t.Id + " построено: " + Math.Round(dist) + " м, пол на высоте " + Math.Round(floorY) + " м.");
		}
		else if (cmd == "del")
		{
			int delId = 0;
			if (args.Count() >= 3)
				delId = args[2].ToInt();
			else
				delId = FindNearestTunnel(here, 40.0);
			DrezinaTunnelData dt = m_Tunnels.Get(delId);
			if (!dt)
			{
				DrezinaTrackManager.Notify(sender, "Метро не найдено (укажите номер или встаньте у входа).");
				return;
			}
			DespawnTunnel(delId);
			DrezinaTrackManager.Get().DeleteTrack(dt.TrackId);
			m_Tunnels.Remove(delId);
			Save();
			DrezinaTrackManager.Notify(sender, "Метро #" + delId + " удалено.");
		}
		else if (cmd == "list")
		{
			string msg = "";
			foreach (int lid, DrezinaTunnelData lt : m_Tunnels)
				msg += "#" + lid + " " + Math.Round(FlatDistance(lt.A, lt.B)) + "м (" + Math.Round(lt.A[0]) + "," + Math.Round(lt.A[2]) + ")->(" + Math.Round(lt.B[0]) + "," + Math.Round(lt.B[2]) + "); ";
			if (msg == "")
				msg = "Метро нет.";
			DrezinaTrackManager.Notify(sender, msg);
		}
		else if (cmd == "preset")
		{
			draft.A = Vector(PRESET_AX, GetGame().SurfaceY(PRESET_AX, PRESET_AZ), PRESET_AZ);
			draft.B = Vector(PRESET_BX, GetGame().SurfaceY(PRESET_BX, PRESET_BZ), PRESET_BZ);
			draft.HasA = true;
			draft.HasB = true;
			DrezinaTrackManager.Notify(sender, "Раскладка Старый Собор - Выбор (" + Math.Round(FlatDistance(draft.A, draft.B)) + " м). Проверьте места: /metro tp a, /metro tp b. Строить: /metro build");
		}
		else if (cmd == "tp" && args.Count() == 3)
		{
			// /metro tp a | b — к точке черновика, /metro tp 1 — ко входу метро №1
			string which = args[2];
			which.ToLower();
			vector tpPos = vector.Zero;
			if (which == "a" && draft.HasA)
				tpPos = draft.A;
			else if (which == "b" && draft.HasB)
				tpPos = draft.B;
			else if (m_Tunnels.Get(which.ToInt()))
				tpPos = GetSurfaceSpawn(m_Tunnels.Get(which.ToInt()), 0);
			if (tpPos != vector.Zero)
				admin.SetPosition(Vector(tpPos[0], GetGame().SurfaceY(tpPos[0], tpPos[2]) + 0.2, tpPos[2]));
		}
		else if (cmd == "tp")
		{
			// /metro tp <x> <z>  — телепорт на поверхность по координатам карты
			if (args.Count() >= 4)
			{
				float x = args[2].ToFloat();
				float z = args[3].ToFloat();
				admin.SetPosition(Vector(x, GetGame().SurfaceY(x, z) + 0.2, z));
			}
		}
		else if (cmd == "rebuild")
		{
			foreach (int rid, DrezinaTunnelData rt : m_Tunnels)
				SpawnTunnel(rt);
			DrezinaTrackManager.Notify(sender, "Метро пересоздано.");
		}
		else
		{
			DrezinaTrackManager.Notify(sender, "/metro preset | a | b | info | build [глубина] | del [id] | list | tp a|b|<id>|<x> <z> | rebuild");
		}
	}

	int FindNearestTunnel(vector p, float maxDist)
	{
		int best = 0;
		float bestD = maxDist;
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			float da = FlatDistance(p, t.A);
			float db = FlatDistance(p, t.B);
			float du = Math.Min(vector.Distance(p, Under(t, t.A)), vector.Distance(p, Under(t, t.B)));
			float d = Math.Min(Math.Min(da, db), du);
			if (d < bestD)
			{
				bestD = d;
				best = id;
			}
		}
		return best;
	}
}
