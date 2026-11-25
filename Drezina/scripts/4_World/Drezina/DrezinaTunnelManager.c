// Метро: тоннель с поворотами, двумя станциями, павильонами-входами на поверхности и рельсами внутри.
//
// В рельефе DayZ нельзя сделать дыру, поэтому в метро попадают через павильон:
// «Спуститься в метро» переносит игрока на подземную станцию, лестница на станции — обратно наверх.
//
// Где находится сам тоннель:
//  - «под землёй»: прямо под маршрутом, ниже самой низкой точки рельефа на заданную глубину;
//  - «в локации»: если под землёй нельзя (берег, низина — пол ушёл бы ниже уровня моря и игрок «поплыл»),
//    тоннель той же формы и длины строится в отдельной локации за картой (над морем, MetroZone* в settings.json).
//    Игрок этого не замечает: спустился в павильон на берегу — вышел из павильона в городе.
//
// Админ: "/metro a" на месте входа, "/metro via" в местах поворотов (или "/metro auto 25" и просто идти),
// "/metro b" на месте выхода, затем "/metro build".

class DrezinaMetroDraft
{
	ref array<vector> Points = new array<vector>; // A, повороты...
	vector B;
	bool HasB;
	float AutoStep;
	PlayerBase Admin;

	bool HasA()
	{
		return Points.Count() > 0;
	}

	void GetRoute(array<vector> outRoute)
	{
		outRoute.InsertAll(Points);
		if (HasB)
			outRoute.Insert(B);
	}
}

class DrezinaTunnelManager
{
	// Готовая раскладка для Черноруси (координаты X, Z примерные): Старый Собор -> Выбор, ~2.3 км, по плато.
	static const float PRESET_AX = 5900;
	static const float PRESET_AZ = 7800;
	static const float PRESET_BX = 3800;
	static const float PRESET_BZ = 8700;

	static ref DrezinaTunnelManager s_Instance;

	ref map<int, ref DrezinaTunnelData> m_Tunnels = new map<int, ref DrezinaTunnelData>;
	ref map<int, ref DrezinaTrack> m_Splines = new map<int, ref DrezinaTrack>;   // ось тоннеля (под землёй/в локации)
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
			if (!t || t.Route.Count() < 2)
				continue;
			m_Tunnels.Set(t.Id, t);
			SpawnTunnel(t);
		}
		Print("[Drezina] loaded tunnels: " + m_Tunnels.Count());
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(Tick, 250, true);
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

	// авто-точки поворотов, пока админ идёт
	void Tick()
	{
		foreach (string uid, DrezinaMetroDraft d : m_Drafts)
		{
			if (!d || d.AutoStep <= 0 || !d.Admin || !d.HasA())
				continue;
			vector p = d.Admin.GetPosition();
			if (FlatDistance(d.Points[d.Points.Count() - 1], p) >= d.AutoStep)
				d.Points.Insert(p);
		}
	}

	// ------------------------------------------------------------------ геометрия

	static vector Side(vector dir)
	{
		return Vector(dir[2], 0, -dir[0]).Normalized();
	}

	static float FlatDistance(vector a, vector b)
	{
		a[1] = 0;
		b[1] = 0;
		return vector.Distance(a, b);
	}

	static vector ToUnder(DrezinaTunnelData t, vector surface)
	{
		return Vector(surface[0] + t.Offset[0], t.FloorY, surface[2] + t.Offset[2]);
	}

	// Сплайн по точкам маршрута на фиксированной высоте y (форма та же, что у рельсов).
	static DrezinaTrack MakeSpline(array<vector> route, vector offset, float y)
	{
		DrezinaTrackData td = new DrezinaTrackData();
		foreach (vector p : route)
			td.Nodes.Insert(Vector(p[0] + offset[0], y, p[2] + offset[2]));
		return new DrezinaTrack(td);
	}

	DrezinaTrack GetSpline(DrezinaTunnelData t)
	{
		DrezinaTrack s = m_Splines.Get(t.Id);
		if (!s)
		{
			s = MakeSpline(t.Route, t.Offset, t.FloorY);
			m_Splines.Set(t.Id, s);
		}
		return s;
	}

	// Самая низкая точка рельефа над осью тоннеля (с запасом по ширине и за станциями).
	static float MinSurfaceAlong(array<vector> route)
	{
		DrezinaTrack s = MakeSpline(route, vector.Zero, 0);
		float minY = 100000;
		float len = s.GetLength();
		float d = -DrezinaConst.STATION_BACK;
		while (d <= len + DrezinaConst.STATION_BACK)
		{
			vector pos, dir;
			s.GetPosDir(Math.Clamp(d, 0, len), pos, dir);
			if (d < 0)
				pos = pos + dir * d;
			else if (d > len)
				pos = pos + dir * (d - len);
			vector side = Side(dir);
			for (int k = -1; k <= 1; k++)
			{
				vector p = pos + side * (k * 6.0);
				float y = GetGame().SurfaceY(p[0], p[2]);
				if (y < minY)
					minY = y;
			}
			d += 4.0;
		}
		return minY;
	}

	// Сдвиг для новой локации за картой: тоннели раскладываются друг за другом по Z.
	vector NextZoneOffset(array<vector> route)
	{
		DrezinaSettings st = DrezinaSettings.Get();
		float startZ = st.MetroZoneZ;
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			if (!t.Zone)
				continue;
			foreach (vector p : t.Route)
				startZ = Math.Max(startZ, p[2] + t.Offset[2] + 40 + st.MetroZoneGap);
		}
		float minX = 1000000;
		float minZ = 1000000;
		foreach (vector q : route)
		{
			minX = Math.Min(minX, q[0]);
			minZ = Math.Min(minZ, q[2]);
		}
		// запас 40 м на станции и изгибы сплайна
		return Vector(st.MetroZoneX + 40 - minX, 0, startZ + 40 - minZ);
	}

	// Конец тоннеля: точка на оси, направление пути (A->B) и направление «внутрь тоннеля».
	void GetEnd(DrezinaTunnelData t, int end, out vector pos, out vector dirTrack, out vector inward)
	{
		DrezinaTrack s = GetSpline(t);
		float d = 0;
		if (end == 1)
			d = s.GetLength();
		s.GetPosDir(d, pos, dirTrack);
		dirTrack[1] = 0;
		dirTrack.Normalize();
		inward = dirTrack;
		if (end == 1)
			inward = dirTrack * -1;
	}

	// После спуска: у лестницы на станции. Станции выдачи стоят справа от пути, лестница — слева.
	vector GetStationSpawn(DrezinaTunnelData t, int end)
	{
		vector pos, dirT, inward;
		GetEnd(t, end, pos, dirT, inward);
		return pos - inward * 2.0 - Side(dirT) * 3.0 + Vector(0, 0.05, 0);
	}

	// После подъёма: перед дверью павильона.
	vector GetSurfaceSpawn(DrezinaTunnelData t, int end)
	{
		vector pos, dirT, inward;
		GetEnd(t, end, pos, dirT, inward);
		vector surf = t.Route[0];
		if (end == 1)
			surf = t.Route[t.Route.Count() - 1];
		vector p = surf + inward * 3.0;
		p[1] = GetGame().SurfaceY(p[0], p[2]) + 0.05;
		return p;
	}

	// ------------------------------------------------------------------ спавн

	void SpawnTunnel(DrezinaTunnelData t)
	{
		DespawnTunnel(t.Id);
		m_Splines.Remove(t.Id);
		array<Object> objs = new array<Object>;

		DrezinaTrack s = GetSpline(t);
		float len = s.GetLength();
		float stCenter = DrezinaConst.STATION_LEN * 0.5 - DrezinaConst.STATION_BACK;

		// станции (открытым торцом в тоннель)
		vector pA, dA, iA, pB, dB, iB;
		GetEnd(t, 0, pA, dA, iA);
		GetEnd(t, 1, pB, dB, iB);
		AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_MetroStation", pA + iA * stCenter, iA));
		AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_MetroStation", pB + iB * stCenter, iB));

		// тоннель: на прямых — звенья 10 м, на поворотах — короткие с нахлёстом
		float tStart = DrezinaConst.STATION_LEN - DrezinaConst.STATION_BACK;
		float tEnd = len - tStart;
		float d = tStart;
		while (d < tEnd - 0.01)
		{
			string type = "Drezina_Tunnel2";
			float piece = DrezinaConst.TUNNEL_SHORT_STEP;
			if (d + DrezinaConst.TUNNEL_PIECE_LEN <= tEnd && DrezinaTrackManager.IsStraight(s, d, d + DrezinaConst.TUNNEL_PIECE_LEN))
			{
				type = "Drezina_Tunnel10";
				piece = DrezinaConst.TUNNEL_PIECE_LEN;
			}
			float c = d + piece * 0.5;
			if (c + piece * 0.5 > tEnd)
				c = tEnd - piece * 0.5;
			vector pos, dir;
			s.GetPosDir(c, pos, dir);
			dir[1] = 0;
			AddObj(objs, DrezinaTrackManager.SpawnStatic(type, pos, dir.Normalized()));
			d += piece;
		}

		// светильники под сводом
		float lampD = 2.0;
		while (lampD < len - 2.0)
		{
			vector lp, ld;
			s.GetPosDir(lampD, lp, ld);
			ld[1] = 0;
			AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_TunnelLamp", lp + Vector(0, 4.3, 0), ld.Normalized()));
			lampD += DrezinaConst.LAMP_STEP;
		}

		SpawnEntrance(t, 0, objs);
		SpawnEntrance(t, 1, objs);
		m_Objects.Set(t.Id, objs);

		// путь внутри: те же узлы, что и ось тоннеля, + высота рельса
		if (t.TrackId == 0 || !DrezinaTrackManager.Get().GetTrack(t.TrackId))
		{
			array<vector> nodes = new array<vector>;
			vector railUp = Vector(0, DrezinaConst.RAIL_TOP_ABOVE_FLOOR, 0);
			foreach (vector rp : t.Route)
				nodes.Insert(ToUnder(t, rp) + railUp);
			t.TrackId = DrezinaTrackManager.Get().CreateTrack(nodes, "Метро " + t.Id);
			Save();
		}
	}

	void SpawnEntrance(DrezinaTunnelData t, int end, array<Object> objs)
	{
		vector pos, dirT, inward;
		GetEnd(t, end, pos, dirT, inward);

		vector surf = t.Route[0];
		if (end == 1)
			surf = t.Route[t.Route.Count() - 1];
		surf[1] = GetGame().SurfaceY(surf[0], surf[2]);
		Drezina_MetroHatch hatch = Drezina_MetroHatch.Cast(DrezinaTrackManager.SpawnStatic("Drezina_MetroHatch", surf, inward));
		if (hatch)
		{
			hatch.m_TunnelId = t.Id;
			hatch.m_End = end;
			objs.Insert(hatch);
		}

		vector lPos = pos - inward * (DrezinaConst.STATION_BACK - 0.6) - Side(dirT) * 3.0;
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
		vector pos, dirT, inward;
		GetEnd(t, end, pos, dirT, inward);
		if (down)
			player.SetPosition(GetStationSpawn(t, end));
		else
			player.SetPosition(GetSurfaceSpawn(t, end));
		player.SetDirection(inward);
	}

	// ------------------------------------------------------------------ постройка

	// mode: "auto" (под землёй, если можно, иначе в локации), "under", "zone"
	void Build(PlayerIdentity sender, DrezinaMetroDraft draft, string mode, float depth)
	{
		array<vector> route = new array<vector>;
		draft.GetRoute(route);
		if (route.Count() < 2 || !draft.HasB)
		{
			DrezinaTrackManager.Notify(sender, "Нужны вход и выход: /metro a ... /metro b");
			return;
		}

		DrezinaTrack flat = MakeSpline(route, vector.Zero, 0);
		float len = flat.GetLength();
		if (len < DrezinaConst.METRO_MIN_LEN)
		{
			DrezinaTrackManager.Notify(sender, "Слишком коротко: нужно хотя бы " + DrezinaConst.METRO_MIN_LEN + " м.");
			return;
		}

		DrezinaSettings st = DrezinaSettings.Get();
		DrezinaTunnelData t = new DrezinaTunnelData();
		t.Id = NextId();
		t.Route.InsertAll(route);

		float floorY = MinSurfaceAlong(route) - depth;
		bool canUnder = floorY >= st.MetroMinFloorY;

		if (mode == "under" && !canUnder)
		{
			DrezinaTrackManager.Notify(sender, "Под землёй нельзя: пол ушёл бы ниже уровня моря. Используйте /metro build zone");
			return;
		}

		if (mode == "zone" || (mode == "auto" && !canUnder))
		{
			t.Zone = true;
			t.Offset = NextZoneOffset(route);
			t.FloorY = st.MetroZoneY;
		}
		else
		{
			t.Zone = false;
			t.Offset = vector.Zero;
			t.FloorY = floorY;
		}

		m_Tunnels.Set(t.Id, t);
		SpawnTunnel(t);
		Save();

		string where = "под землёй, пол на высоте " + Math.Round(t.FloorY) + " м";
		if (t.Zone)
			where = "в локации за картой";
		DrezinaTrackManager.Notify(sender, "Метро #" + t.Id + " построено " + where + ", длина " + Math.Round(len) + " м.");
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
		draft.Admin = admin;
		vector here = admin.GetPosition();

		if (cmd == "a")
		{
			draft.Points.Clear();
			draft.Points.Insert(here);
			draft.HasB = false;
			DrezinaTrackManager.Notify(sender, "Вход A запомнен. Повороты: /metro via (или /metro auto 25), выход: /metro b");
		}
		else if (cmd == "via")
		{
			if (!draft.HasA())
			{
				DrezinaTrackManager.Notify(sender, "Сначала /metro a");
				return;
			}
			draft.Points.Insert(here);
			DrezinaTrackManager.Notify(sender, "Точка поворота " + (draft.Points.Count() - 1) + " добавлена.");
		}
		else if (cmd == "auto")
		{
			float step = 0;
			if (args.Count() >= 3)
				step = args[2].ToFloat();
			if (step > 0 && step < 10)
				step = 10;
			draft.AutoStep = step;
			if (step > 0)
				DrezinaTrackManager.Notify(sender, "Авто-точки каждые " + step + " м. Выключить: /metro auto 0");
			else
				DrezinaTrackManager.Notify(sender, "Авто-точки выключены.");
		}
		else if (cmd == "undo")
		{
			if (draft.HasB)
				draft.HasB = false;
			else if (draft.Points.Count() > 1)
				draft.Points.Remove(draft.Points.Count() - 1);
			DrezinaTrackManager.Notify(sender, "Последняя точка убрана.");
		}
		else if (cmd == "b")
		{
			if (!draft.HasA())
			{
				DrezinaTrackManager.Notify(sender, "Сначала /metro a");
				return;
			}
			draft.B = here;
			draft.HasB = true;
			draft.AutoStep = 0;
			array<vector> r = new array<vector>;
			draft.GetRoute(r);
			DrezinaTrackManager.Notify(sender, "Выход B запомнен. Длина ~" + Math.Round(MakeSpline(r, vector.Zero, 0).GetLength()) + " м. /metro info или /metro build");
		}
		else if (cmd == "info")
		{
			array<vector> ri = new array<vector>;
			draft.GetRoute(ri);
			if (ri.Count() < 2 || !draft.HasB)
			{
				DrezinaTrackManager.Notify(sender, "Нужны вход и выход: /metro a ... /metro b");
				return;
			}
			float depthI = DrezinaSettings.Get().MetroDefaultDepth;
			float floorI = MinSurfaceAlong(ri) - depthI;
			string modeI = "под землёй, пол на " + Math.Round(floorI) + " м";
			if (floorI < DrezinaSettings.Get().MetroMinFloorY)
				modeI = "под землёй нельзя (низко) — будет в локации за картой";
			DrezinaTrackManager.Notify(sender, "Длина " + Math.Round(MakeSpline(ri, vector.Zero, 0).GetLength()) + " м, точек " + ri.Count() + ", " + modeI);
		}
		else if (cmd == "build")
		{
			// /metro build [under|zone] [глубина]
			string mode = "auto";
			float depth = DrezinaSettings.Get().MetroDefaultDepth;
			for (int i = 2; i < args.Count(); i++)
			{
				string arg = args[i];
				arg.ToLower();
				if (arg == "under" || arg == "zone")
					mode = arg;
				else if (arg.ToFloat() > 0)
					depth = Math.Max(arg.ToFloat(), 8.0);
			}
			Build(sender, draft, mode, depth);
			m_Drafts.Remove(uid);
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
			m_Splines.Remove(delId);
			Save();
			DrezinaTrackManager.Notify(sender, "Метро #" + delId + " удалено.");
		}
		else if (cmd == "list")
		{
			string msg = "";
			foreach (int lid, DrezinaTunnelData lt : m_Tunnels)
			{
				string kind = "под землёй";
				if (lt.Zone)
					kind = "локация";
				msg += "#" + lid + " " + Math.Round(GetSpline(lt).GetLength()) + "м, " + kind + "; ";
			}
			if (msg == "")
				msg = "Метро нет.";
			DrezinaTrackManager.Notify(sender, msg);
		}
		else if (cmd == "preset")
		{
			draft.Points.Clear();
			draft.Points.Insert(Vector(PRESET_AX, GetGame().SurfaceY(PRESET_AX, PRESET_AZ), PRESET_AZ));
			draft.B = Vector(PRESET_BX, GetGame().SurfaceY(PRESET_BX, PRESET_BZ), PRESET_BZ);
			draft.HasB = true;
			DrezinaTrackManager.Notify(sender, "Раскладка Старый Собор - Выбор. Проверьте места: /metro tp a, /metro tp b. Строить: /metro build");
		}
		else if (cmd == "tp" && args.Count() == 3)
		{
			// /metro tp a | b — к точкам черновика, /metro tp <id> — ко входу A метро
			string which = args[2];
			which.ToLower();
			vector tpPos = vector.Zero;
			if (which == "a" && draft.HasA())
				tpPos = draft.Points[0];
			else if (which == "b" && draft.HasB)
				tpPos = draft.B;
			else if (m_Tunnels.Get(which.ToInt()))
				tpPos = GetSurfaceSpawn(m_Tunnels.Get(which.ToInt()), 0);
			if (tpPos != vector.Zero)
				admin.SetPosition(Vector(tpPos[0], GetGame().SurfaceY(tpPos[0], tpPos[2]) + 0.2, tpPos[2]));
		}
		else if (cmd == "tp")
		{
			// /metro tp <x> <z>
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
			DrezinaTrackManager.Notify(sender, "/metro a | via | auto <м> | undo | b | info | build [under|zone] [глубина] | preset | del [id] | list | tp a|b|<id>|<x> <z> | rebuild");
		}
	}

	int FindNearestTunnel(vector p, float maxDist)
	{
		int best = 0;
		float bestD = maxDist;
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			for (int end = 0; end <= 1; end++)
			{
				vector surf = t.Route[0];
				if (end == 1)
					surf = t.Route[t.Route.Count() - 1];
				vector pos, dirT, inward;
				GetEnd(t, end, pos, dirT, inward);
				float d = Math.Min(FlatDistance(p, surf), vector.Distance(p, pos));
				if (d < bestD)
				{
					bestD = d;
					best = id;
				}
			}
		}
		return best;
	}
}
