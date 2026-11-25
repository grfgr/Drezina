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
	ref array<ref DrezinaJunction> m_Junctions = new array<ref DrezinaJunction>;  // пересечения метро (залы со стрелками)
	ref map<int, ref array<Object>> m_Objects = new map<int, ref array<Object>>;
	ref map<string, ref DrezinaMetroDraft> m_Drafts = new map<string, ref DrezinaMetroDraft>;

	// свет: светильники каждого конца тоннеля (ключ = id * 2 + конец) и генераторы на станциях
	ref map<int, ref array<Drezina_TunnelLamp>> m_Lamps = new map<int, ref array<Drezina_TunnelLamp>>;
	ref map<int, EntityAI> m_Generators = new map<int, EntityAI>;
	ref map<int, bool> m_Powered = new map<int, bool>;
	float m_PowerTimer;

	// клиент: маршруты метро на поверхности (для карты КПК)
	ref array<ref DrezinaTunnelData> m_ClientTunnels = new array<ref DrezinaTunnelData>;

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
		}
		RespawnAll();
		Print("[Drezina] loaded tunnels: " + m_Tunnels.Count() + ", пересечений: " + m_Junctions.Count());
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(Tick, 250, true);
	}

	// ------------------------------------------------------------------ данные метро клиентам (карта КПК)

	void WriteTunnels(ScriptRPC rpc)
	{
		int c = m_Tunnels.Count();
		rpc.Write(c);
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			rpc.Write(t.Id);
			rpc.Write(t.Zone);
			int n = t.Route.Count();
			rpc.Write(n);
			for (int i = 0; i < n; i++)
				rpc.Write(t.Route[i]);
		}
	}

	void SendAllTo(PlayerIdentity identity)
	{
		if (!identity || !identity.GetPlayer())
			return;
		ScriptRPC rpc = new ScriptRPC();
		WriteTunnels(rpc);
		rpc.Send(identity.GetPlayer(), DrezinaRPC.TUNNELS_FULL, true, identity);
	}

	void BroadcastAll()
	{
		array<Man> players = new array<Man>;
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			if (m && m.GetIdentity())
				SendAllTo(m.GetIdentity());
		}
	}

	bool ClientOnRPC(int rpc_type, ParamsReadContext ctx)
	{
		if (rpc_type != DrezinaRPC.TUNNELS_FULL)
			return false;
		m_ClientTunnels.Clear();
		int c;
		if (!ctx.Read(c))
			return true;
		for (int i = 0; i < c; i++)
		{
			DrezinaTunnelData t = new DrezinaTunnelData();
			int n;
			if (!ctx.Read(t.Id) || !ctx.Read(t.Zone) || !ctx.Read(n))
				return true;
			for (int k = 0; k < n; k++)
			{
				vector v;
				if (!ctx.Read(v))
					return true;
				t.Route.Insert(v);
			}
			m_ClientTunnels.Insert(t);
		}
		Print("[Drezina] клиент: получено метро " + m_ClientTunnels.Count());
		return true;
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
		UpdatePower(0.25);

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

	// Бункер у конца тоннеля: за глухой стеной станции — коридор, за ним лестничная шахта.
	// side = +X моделей (вправо, если смотреть в тоннель).
	void GetBunkerFrame(DrezinaTunnelData t, int end, out vector endPos, out vector inward, out vector side)
	{
		vector dirT;
		GetEnd(t, end, endPos, dirT, inward);
		side = Side(inward);
	}

	vector GetCorridorPos(DrezinaTunnelData t, int end, out vector inward)
	{
		vector e, side;
		GetBunkerFrame(t, end, e, inward, side);
		return e - inward * (DrezinaConst.STATION_BACK + DrezinaConst.CORRIDOR_LEN * 0.5) + side * DrezinaConst.BUNKER_SIDE_X;
	}

	// Origin модели лестницы = пол шахты в центре.
	vector GetStairsPos(DrezinaTunnelData t, int end, out vector inward)
	{
		vector e, side;
		GetBunkerFrame(t, end, e, inward, side);
		float back = DrezinaConst.STATION_BACK + DrezinaConst.CORRIDOR_LEN + DrezinaConst.BUNKER_WALL + DrezinaConst.STAIR_HALF_Y;
		return e - inward * back + side * DrezinaConst.BUNKER_SIDE_X;
	}

	// После спуска: верхняя площадка лестницы, спиной к двери — дальше пешком 4 марша вниз.
	vector GetStationSpawn(DrezinaTunnelData t, int end)
	{
		vector inward;
		vector st = GetStairsPos(t, end, inward);
		return st + inward * (DrezinaConst.STAIR_HALF_Y - 0.6) + Vector(0, DrezinaConst.STAIR_TOP + 0.05, 0);
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
		int piece10 = 0;
		// чередование вариантов прямого звена: обычное и 6 «событий» (обвал, ниша ТП, вагонетка, блокпост, протечка, крепь)
		array<string> variants = {"Drezina_Tunnel10", "Drezina_Tunnel10B", "Drezina_Tunnel10E", "Drezina_Tunnel10", "Drezina_Tunnel10C", "Drezina_Tunnel10F", "Drezina_Tunnel10", "Drezina_Tunnel10D", "Drezina_Tunnel10G"};
		while (d < tEnd - 0.01)
		{
			string type = "Drezina_Tunnel2";
			float piece = DrezinaConst.TUNNEL_SHORT_STEP;
			vector jp, jd;
			s.GetPosDir(d + DrezinaConst.TUNNEL_PIECE_LEN * 0.5, jp, jd);
			float jr;
			bool nearJ = JunctionDist(t.Id, jp, jr) < jr + 12.0;   // у зала развязки — короткими звеньями
			if (!nearJ && d + DrezinaConst.TUNNEL_PIECE_LEN <= tEnd && DrezinaTrackManager.IsStraight(s, d, d + DrezinaConst.TUNNEL_PIECE_LEN))
			{
				type = variants[(piece10 * 5 + t.Id) % variants.Count()];
				piece10++;
				piece = DrezinaConst.TUNNEL_PIECE_LEN;
			}
			float c = d + piece * 0.5;
			if (c + piece * 0.5 > tEnd)
				c = tEnd - piece * 0.5;
			vector pos, dir;
			s.GetPosDir(c, pos, dir);
			dir[1] = 0;
			float jr2;
			if (JunctionDist(t.Id, pos, jr2) >= jr2 - 0.2)          // внутри зала развязки тоннеля нет
				AddObj(objs, DrezinaTrackManager.SpawnStatic(type, pos, dir.Normalized()));
			d += piece;
		}

		// бункер у обоих концов: коридор + лестничная шахта (освещения нет — нужен фонарь)
		for (int be = 0; be <= 1; be++)
		{
			vector bInward;
			vector corPos = GetCorridorPos(t, be, bInward);
			AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_BunkerCorridor", corPos, bInward));
			vector stPos = GetStairsPos(t, be, bInward);
			AddObj(objs, DrezinaTrackManager.SpawnStatic("Drezina_BunkerStairs", stPos, bInward));
		}

		SpawnEntrance(t, 0, objs);
		SpawnEntrance(t, 1, objs);
		SpawnLighting(t, objs);
		SpawnDarkness(t, objs);
		m_Objects.Set(t.Id, objs);

		// путь внутри: те же узлы, что и ось тоннеля, + высота рельса
		if (t.TrackId == 0 || !DrezinaTrackManager.Get().GetTrack(t.TrackId))
		{
			array<vector> nodes = new array<vector>;
			// RailHeightOffset добавится при спавне рельсов и дрезины — здесь его вычитаем
			vector railUp = Vector(0, DrezinaConst.RAIL_TOP_ABOVE_FLOOR - DrezinaSettings.Get().RailHeightOffset, 0);
			foreach (vector rp : t.Route)
				nodes.Insert(ToUnder(t, rp) + railUp);
			t.TrackId = DrezinaTrackManager.Get().CreateTrack(nodes, "Метро " + t.Id);
			Save();
		}
	}

	// ------------------------------------------------------------------ темнота и звук подземелья

	// Зоны темноты: лестничные шахты, коридоры, станции и тоннель кусками по 40 м вдоль оси.
	void SpawnDarkness(DrezinaTunnelData t, array<Object> objs)
	{
		int before = objs.Count();
		for (int end = 0; end <= 1; end++)
		{
			vector sIn, cIn;
			vector st = GetStairsPos(t, end, sIn);
			AddObj(objs, DrezinaUnderground.AddZone(st + Vector(0, 6.4, 0), Vector(5.0, 13.6, 8.4), sIn, "drezina stairs " + t.Id));
			vector cor = GetCorridorPos(t, end, cIn);
			AddObj(objs, DrezinaUnderground.AddZone(cor + Vector(0, 1.5, 0), Vector(4.0, 3.6, DrezinaConst.CORRIDOR_LEN + 1.0), cIn, "drezina corridor " + t.Id));
			vector e, dirT, inward;
			GetEnd(t, end, e, dirT, inward);
			vector stc = e + inward * (DrezinaConst.STATION_LEN * 0.5 - DrezinaConst.STATION_BACK);
			AddObj(objs, DrezinaUnderground.AddZone(stc + Vector(0, 2.8, 0), Vector(14.0, 6.6, DrezinaConst.STATION_LEN + 1.0), inward, "drezina station " + t.Id));
		}
		DrezinaTrack s = GetSpline(t);
		float len = s.GetLength();
		float step = 40.0;
		for (float d = 0; d < len; d += step)
		{
			float c = Math.Min(d + step * 0.5, len);
			vector pos, dir;
			s.GetPosDir(c, pos, dir);
			dir[1] = 0;
			AddObj(objs, DrezinaUnderground.AddZone(pos + Vector(0, 2.6, 0), Vector(8.0, 6.4, step + 4.0), dir.Normalized(), "drezina tunnel " + t.Id));
		}
		DrezinaUnderground.SyncAll();
		Print("[Drezina] метро #" + t.Id + ": зон темноты " + (objs.Count() - before));
	}

	// ------------------------------------------------------------------ свет и генераторы

	static int Key(int tunnelId, int end)
	{
		return tunnelId * 2 + end;
	}

	Drezina_TunnelLamp SpawnLamp(int key, vector pos, vector dir, array<Object> objs)
	{
		int flags = ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN | ECE_NOLIFETIME | ECE_NOPERSISTENCY_WORLD;
		Drezina_TunnelLamp lamp = Drezina_TunnelLamp.Cast(GetGame().CreateObjectEx("Drezina_TunnelLamp", pos, flags, RF_DEFAULT));
		if (!lamp)
			return null;
		lamp.SetPosition(pos);
		lamp.SetDirection(dir);
		lamp.Update();
		objs.Insert(lamp);
		array<Drezina_TunnelLamp> group = m_Lamps.Get(key);
		if (!group)
		{
			group = new array<Drezina_TunnelLamp>;
			m_Lamps.Set(key, group);
		}
		group.Insert(lamp);
		return lamp;
	}

	// Генератор стоит на бетонной площадке у глухой стены станции (справа от пути).
	vector GetGeneratorPos(DrezinaTunnelData t, int end, out vector inward)
	{
		vector e, side;
		GetBunkerFrame(t, end, e, inward, side);
		return e - inward * 2.0 + side * 4.5 + Vector(0, 0.2, 0);
	}

	EntityAI SpawnGenerator(DrezinaTunnelData t, int end)
	{
		vector inward;
		vector pos = GetGeneratorPos(t, end, inward);
		int flags = ECE_CREATEPHYSICS | ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN | ECE_NOLIFETIME | ECE_NOPERSISTENCY_WORLD;
		EntityAI gen = EntityAI.Cast(GetGame().CreateObjectEx(DrezinaSettings.Get().MetroGeneratorType, pos, flags, RF_DEFAULT));
		if (!gen)
		{
			Print("[Drezina] !!! генератор не создан: " + DrezinaSettings.Get().MetroGeneratorType);
			return null;
		}
		gen.SetPosition(pos);
		gen.SetDirection(Side(inward) * -1);
		m_Generators.Set(Key(t.Id, end), gen);
		return gen;
	}

	void SpawnLighting(DrezinaTunnelData t, array<Object> objs)
	{
		DrezinaTrack s = GetSpline(t);
		float len = s.GetLength();
		vector up = Vector(0, 1, 0);

		for (int end = 0; end <= 1; end++)
		{
			int key = Key(t.Id, end);
			m_Lamps.Remove(key);
			m_Powered.Set(key, false);

			vector e, inward, side;
			GetBunkerFrame(t, end, e, inward, side);

			// станция: 2 ряда по 4 светильника под сводом
			vector center = e + inward * (DrezinaConst.STATION_LEN * 0.5 - DrezinaConst.STATION_BACK);
			for (int ly = 0; ly < 4; ly++)
			{
				float yy = -8.0 + ly * 6.0;
				SpawnLamp(key, center + side * -3.0 + inward * yy + up * 5.2, inward, objs);
				SpawnLamp(key, center + side * 3.0 + inward * yy + up * 5.2, inward, objs);
			}
			// коридор
			vector cIn;
			vector cor = GetCorridorPos(t, end, cIn);
			SpawnLamp(key, cor + cIn * -2.0 + up * 2.78, cIn, objs);
			SpawnLamp(key, cor + cIn * 2.0 + up * 2.78, cIn, objs);
			// лестница: над каждой площадкой, на боковой стене
			vector sIn;
			vector st = GetStairsPos(t, end, sIn);
			vector sSide = Side(sIn);
			float landY[5] = {2.5, -2.5, 2.5, -2.5, 2.5};
			float landZ[5] = {9.6, 7.2, 4.8, 2.4, 0.0};
			for (int li = 0; li < 5; li++)
				SpawnLamp(key, st + sSide * -1.45 + sIn * landY[li] + up * (landZ[li] + 2.3), sIn, objs);

			// генератор
			EntityAI gen = SpawnGenerator(t, end);
			if (gen)
				objs.Insert(gen);
		}

		// тоннель: каждые LAMP_STEP метров, ближняя половина — к своей станции
		float tStart = DrezinaConst.STATION_LEN - DrezinaConst.STATION_BACK;
		float d = tStart + 5.0;
		while (d < len - tStart)
		{
			vector lp, ld;
			s.GetPosDir(d, lp, ld);
			ld[1] = 0;
			int tkey = Key(t.Id, 0);
			if (d > len * 0.5)
				tkey = Key(t.Id, 1);
			float jr3;
			if (JunctionDist(t.Id, lp, jr3) > jr3 + 1.0)
				SpawnLamp(tkey, lp + up * 4.85, ld.Normalized(), objs);
			d += DrezinaConst.LAMP_STEP;
		}
	}

	// Сервер: генератор работает (заправлен, свеча стоит, включён) — свет в его половине горит.
	void UpdatePower(float dt)
	{
		m_PowerTimer += dt;
		if (m_PowerTimer < DrezinaSettings.Get().MetroPowerCheck)
			return;
		m_PowerTimer = 0;

		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			for (int end = 0; end <= 1; end++)
			{
				int key = Key(id, end);
				EntityAI gen = m_Generators.Get(key);
				if (!gen)
				{
					// генератор уничтожили или он пропал — ставим новый (пустой: без топлива и свечи)
					gen = SpawnGenerator(t, end);
					array<Object> objs = m_Objects.Get(id);
					if (gen && objs)
						objs.Insert(gen);
				}

				vector inward;
				vector spot = GetGeneratorPos(t, end, inward);
				bool on = false;
				if (gen && vector.Distance(gen.GetPosition(), spot) < 6.0 && gen.GetCompEM())
					on = gen.GetCompEM().IsWorking();

				if (m_Powered.Get(key) == on)
					continue;
				m_Powered.Set(key, on);
				array<Drezina_TunnelLamp> group = m_Lamps.Get(key);
				if (group)
				{
					foreach (Drezina_TunnelLamp lamp : group)
					{
						if (lamp)
							lamp.ServerSetOn(on);
					}
				}
			}
		}
	}

	void SpawnEntrance(DrezinaTunnelData t, int end, array<Object> objs)
	{
		vector pos, dirT, inward;
		GetEnd(t, end, pos, dirT, inward);

		vector surf = t.Route[0];
		if (end == 1)
			surf = t.Route[t.Route.Count() - 1];
		// на склоне ставим по самой низкой точке перед фасадом: дверь не засыпана землёй, а фундамент,
		// отмостка и насыпь уходят в землю на 3 м — снизу нигде не видно щели
		vector fwd = inward;
		vector side = Side(inward);
		float minY = GetGame().SurfaceY(surf[0], surf[2]);
		for (int ix = -1; ix <= 1; ix++)
		{
			for (int iz = 0; iz <= 2; iz++)             // перед фасадом (сзади насыпь и фундамент сами уйдут в склон)
			{
				vector q = surf + side * (ix * 2.0) + fwd * (iz * 1.2);
				minY = Math.Min(minY, GetGame().SurfaceY(q[0], q[2]));
			}
		}
		surf[1] = minY - 0.05;
		Drezina_MetroHatch hatch = Drezina_MetroHatch.Cast(DrezinaTrackManager.SpawnStatic("Drezina_MetroHatch", surf, inward));
		if (hatch)
		{
			hatch.m_TunnelId = t.Id;
			hatch.m_End = end;
			objs.Insert(hatch);
		}

		// гермодверь изнутри: на верхней площадке, лицом в шахту
		vector stInward;
		vector stPos = GetStairsPos(t, end, stInward);
		vector lPos = stPos + stInward * (DrezinaConst.STAIR_HALF_Y - 0.15) + Vector(0, DrezinaConst.STAIR_TOP, 0);
		Drezina_MetroLadder ladder = Drezina_MetroLadder.Cast(DrezinaTrackManager.SpawnStatic("Drezina_MetroLadder", lPos, stInward * -1));
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
		{
			player.SetPosition(GetStationSpawn(t, end));
			player.SetDirection(inward * -1);   // лицом к первому маршу
		}
		else
		{
			player.SetPosition(GetSurfaceSpawn(t, end));
			player.SetDirection(inward);        // спиной к гермодвери
		}
	}


	// ================================================================== пересечения линий: залы со стрелками
	//
	// Линии на одном уровне, которые пересекаются вдали от станций (>= 60 м), получают круглый зал
	// радиусом 24 м. Под большим углом (>= 55°) внутри — кольцо R=11 м, с каждой из 4 веток на кольцо
	// съезды налево и направо (руль A/D), прямо — насквозь через центр. Под малым углом (20..55°) —
	// два плавных съезда с линии на линию. Острее 20° — без развязки (тоннели слились бы надолго).

	static const float JUNC_RADIUS = 24.0;
	static const float JUNC_END_CLEAR = 60.0;
	static const float JUNC_RING_R = 11.0;
	static const float JUNC_ARM_R = 20.0;
	static const float JUNC_WYE_L = 15.0;

	// расстояние от точки до ближайшего зала этой линии (и его радиус)
	float JunctionDist(int tunnelId, vector p, out float radius)
	{
		float best = 1000000.0;
		radius = 0;
		foreach (DrezinaJunction j : m_Junctions)
		{
			if (j.A != tunnelId && j.B != tunnelId)
				continue;
			float dd = FlatDistance(p, j.Center);
			if (dd < best)
			{
				best = dd;
				radius = j.Radius;
			}
		}
		return best;
	}

	static vector Flat(vector v)
	{
		v[1] = 0;
		return v.Normalized();
	}

	// пересечение отрезков на плоскости XZ: параметры ta, tb на [0,1]
	static bool SegCross(vector a0, vector a1, vector b0, vector b1, out float ta, out float tb)
	{
		float rx = a1[0] - a0[0];
		float rz = a1[2] - a0[2];
		float sx = b1[0] - b0[0];
		float sz = b1[2] - b0[2];
		float den = rx * sz - rz * sx;
		if (Math.AbsFloat(den) < 0.000001)
			return false;
		float qx = b0[0] - a0[0];
		float qz = b0[2] - a0[2];
		ta = (qx * sz - qz * sx) / den;
		tb = (qx * rz - qz * rx) / den;
		return ta >= 0 && ta <= 1 && tb >= 0 && tb <= 1;
	}

	// первое пересечение двух осей (по 4 м), вдали от концов обеих
	bool FirstCrossing(DrezinaTrack sa, DrezinaTrack sb, out vector x, out float da, out float db, out vector dirA, out vector dirB)
	{
		array<vector> found = new array<vector>;
		array<float> fa = new array<float>;
		array<float> fb = new array<float>;
		AllCrossings(sa, sb, found, fa, fb);
		if (found.Count() == 0)
			return false;
		x = found[0];
		da = fa[0];
		db = fb[0];
		vector p;
		sa.GetPosDir(da, p, dirA);
		sb.GetPosDir(db, p, dirB);
		dirA = Flat(dirA);
		dirB = Flat(dirB);
		return true;
	}

	void AllCrossings(DrezinaTrack sa, DrezinaTrack sb, array<vector> outX, array<float> outDA, array<float> outDB)
	{
		float step = 4.0;
		float la = sa.GetLength();
		float lb = sb.GetLength();
		for (float a = JUNC_END_CLEAR - step; a < la - JUNC_END_CLEAR + step; a += step)
		{
			vector a0, a1, dd;
			sa.GetPosDir(a, a0, dd);
			sa.GetPosDir(a + step, a1, dd);
			for (float b = JUNC_END_CLEAR - step; b < lb - JUNC_END_CLEAR + step; b += step)
			{
				vector b0, b1;
				sb.GetPosDir(b, b0, dd);
				sb.GetPosDir(b + step, b1, dd);
				float ta, tb;
				if (!SegCross(a0, a1, b0, b1, ta, tb))
					continue;
				float da = a + ta * step;
				float db = b + tb * step;
				if (da < JUNC_END_CLEAR || da > la - JUNC_END_CLEAR || db < JUNC_END_CLEAR || db > lb - JUNC_END_CLEAR)
					continue;
				vector x = a0 + (a1 - a0) * ta;
				bool dup = false;
				foreach (vector fx : outX)
				{
					if (FlatDistance(fx, x) < JUNC_RADIUS * 2.5)
						dup = true;
				}
				if (dup)
					continue;
				outX.Insert(x);
				outDA.Insert(da);
				outDB.Insert(db);
			}
		}
	}

	// Пересекающиеся линии с разницей пола до 6 м выравниваем: более новая (больший номер) встаёт на уровень
	// старой, если над ней остаётся хотя бы 4 м земли. Иначе зала со стрелками не получится, а тоннели
	// врезаются друг в друга (дрезина упирается в стену чужого тоннеля).
	void LevelCrossings()
	{
		bool changed = false;
		foreach (int ia, DrezinaTunnelData a : m_Tunnels)
		{
			foreach (int ib, DrezinaTunnelData b : m_Tunnels)
			{
				if (a.Id >= b.Id || a.Zone || b.Zone)
					continue;
				float diff = Math.AbsFloat(a.FloorY - b.FloorY);
				if (diff <= 0.3 || diff > 6.0)
					continue;
				array<vector> xs = new array<vector>;
				array<float> das = new array<float>;
				array<float> dbs = new array<float>;
				AllCrossings(GetSpline(a), GetSpline(b), xs, das, dbs);
				if (xs.Count() == 0)
					continue;
				float top = MinSurfaceAlong(b.Route) - 4.0;
				if (a.FloorY > top)
				{
					Print("[Drezina] метро #" + b.Id + " не поднять до уровня #" + a.Id + ": над ним не останется земли");
					continue;
				}
				Print("[Drezina] метро #" + b.Id + ": пол " + b.FloorY + " -> " + a.FloorY + " (на уровень #" + a.Id + " для развязки)");
				b.FloorY = a.FloorY;
				m_Splines.Remove(b.Id);
				// путь внутри — на новую высоту
				DrezinaTrack tr = DrezinaTrackManager.Get().GetTrack(b.TrackId);
				if (tr)
				{
					array<vector> nodes = new array<vector>;
					vector railUp = Vector(0, DrezinaConst.RAIL_TOP_ABOVE_FLOOR - DrezinaSettings.Get().RailHeightOffset, 0);
					foreach (vector rp : b.Route)
						nodes.Insert(ToUnder(b, rp) + railUp);
					DrezinaTrackManager.Get().ReplaceNodes(b.TrackId, nodes);
				}
				changed = true;
			}
		}
		if (changed)
			Save();
	}

	void ComputeJunctions()
	{
		m_Junctions.Clear();
		array<DrezinaTunnelData> list = new array<DrezinaTunnelData>;
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
		{
			if (!t.Zone)
				list.Insert(t);
		}
		for (int i = 0; i < list.Count(); i++)
		{
			for (int k = i + 1; k < list.Count(); k++)
			{
				DrezinaTunnelData a = list[i];
				DrezinaTunnelData b = list[k];
				if (Math.AbsFloat(a.FloorY - b.FloorY) > 0.3)
					continue;
				DrezinaTrack sa = GetSpline(a);
				DrezinaTrack sb = GetSpline(b);
				array<vector> xs = new array<vector>;
				array<float> das = new array<float>;
				array<float> dbs = new array<float>;
				AllCrossings(sa, sb, xs, das, dbs);
				for (int n = 0; n < xs.Count(); n++)
				{
					bool clash = false;
					foreach (DrezinaJunction ej : m_Junctions)
					{
						if (FlatDistance(ej.Center, xs[n]) < JUNC_RADIUS * 2.5)
							clash = true;
					}
					if (clash)
						continue;
					vector p, dA, dB;
					sa.GetPosDir(das[n], p, dA);
					sb.GetPosDir(dbs[n], p, dB);
					dA = Flat(dA);
					dB = Flat(dB);
					float cosv = Math.AbsFloat(vector.Dot(dA, dB));
					float ang = Math.Acos(Math.Clamp(cosv, 0, 1)) * Math.RAD2DEG;
					if (ang < 20)
					{
						Print("[Drezina] пересечение метро #" + a.Id + " и #" + b.Id + " слишком острое (" + Math.Round(ang) + "°) — без развязки");
						continue;
					}
					DrezinaJunction j = new DrezinaJunction();
					j.A = a.Id;
					j.B = b.Id;
					j.Center = Vector(xs[n][0], a.FloorY, xs[n][2]);
					j.DirA = dA;
					j.DirB = dB;
					j.Ring = ang >= 55;
					j.Radius = JUNC_RADIUS;
					m_Junctions.Insert(j);
					Print("[Drezina] пересечение метро #" + a.Id + " и #" + b.Id + ": " + Math.Round(ang) + "°, кольцо=" + j.Ring);
				}
			}
		}
	}

	// всё метро заново: пересечения -> тоннели (с пропуском залов) -> залы, служебные пути и стрелки
	void RespawnAll()
	{
		foreach (DrezinaJunction oj : m_Junctions)
		{
			foreach (Object o : oj.Objects)
			{
				if (o)
					GetGame().ObjectDelete(o);
			}
		}
		DrezinaTrackManager.Get().RemoveServiceTracks();
		m_Splines.Clear();
		LevelCrossings();
		ComputeJunctions();
		foreach (int id, DrezinaTunnelData t : m_Tunnels)
			SpawnTunnel(t);
		foreach (DrezinaJunction j : m_Junctions)
			SpawnJunction(j);
		DrezinaUnderground.SyncAll();
		DrezinaTrackManager.Get().ServerJunctionsChanged();
	}

	static vector ArmDir(float ang)
	{
		return Vector(Math.Sin(ang), 0, Math.Cos(ang));
	}

	static float DirAngle(vector d)
	{
		return Math.Atan2(d[0], d[2]);
	}

	static vector Hermite(vector p0, vector m0, vector p1, vector m1, float s)
	{
		float s2 = s * s;
		float s3 = s2 * s;
		return p0 * (2 * s3 - 3 * s2 + 1) + m0 * (s3 - 2 * s2 + s) + p1 * (-2 * s3 + 3 * s2) + m1 * (s3 - s2);
	}

	static int SideSign(vector motion, vector from, vector to)
	{
		if (vector.Dot(Side(Flat(motion)), to - from) >= 0)
			return 1;
		return -1;
	}

	// съезд: узлы по кривой Эрмита от p0 (касательная t0) до p1 (касательная t1)
	static void ConnectorNodes(vector p0, vector t0, vector p1, vector t1, float y, array<vector> nodes)
	{
		float L = FlatDistance(p0, p1);
		for (int i = 0; i <= 10; i++)
		{
			float sp = i;
			sp = sp / 10.0;
			vector q = Hermite(p0, t0 * L, p1, t1 * L, sp);
			q[1] = y;
			nodes.Insert(q);
		}
	}

	void SpawnJunction(DrezinaJunction j)
	{
		DrezinaTunnelData ta = m_Tunnels.Get(j.A);
		DrezinaTunnelData tb = m_Tunnels.Get(j.B);
		if (!ta || !tb)
			return;
		DrezinaTrackManager tm = DrezinaTrackManager.Get();
		DrezinaTrack ma = tm.GetTrack(ta.TrackId);
		DrezinaTrack mb = tm.GetTrack(tb.TrackId);
		if (!ma || !mb)
			return;
		vector c = j.Center;
		float R = j.Radius;

		// зал: пол, свод на балках; стены панелями по кругу, у входа каждой ветки — портал под тоннель
		AddObj(j.Objects, DrezinaTrackManager.SpawnStatic("Drezina_JunctionHall", c, j.DirA));
		array<vector> arms = new array<vector>;
		arms.Insert(j.DirA);
		arms.Insert(j.DirA * -1.0);
		arms.Insert(j.DirB);
		arms.Insert(j.DirB * -1.0);
		foreach (vector arm : arms)
			AddObj(j.Objects, DrezinaTrackManager.SpawnStatic("Drezina_JunctionPortal", c + arm * R, arm * -1.0));
		float stepA = 2.7 / (R + 0.25);
		float gap = Math.Asin(4.4 / R);          // панели с центром ближе 4.4 м к оси входа — за порталом (он 12 м)
		for (float ang = 0; ang < Math.PI2 - stepA * 0.5; ang += stepA)
		{
			vector o = ArmDir(ang);
			bool skip = false;
			foreach (vector a2 : arms)
			{
				if (vector.Dot(o, a2) > Math.Cos(gap))
					skip = true;
			}
			if (!skip)
				AddObj(j.Objects, DrezinaTrackManager.SpawnStatic("Drezina_JunctionWall", c + o * (R + 0.25), o * -1.0));
		}
		AddObj(j.Objects, DrezinaUnderground.AddZone(c + Vector(0, 3.4, 0), Vector(R * 2 + 1, 7.2, R * 2 + 1), j.DirA, "drezina junction " + j.A + "x" + j.B));
		// свет зала — от генератора ближней станции линии A
		for (int li = 0; li < 8; li++)
		{
			vector lo = ArmDir(DirAngle(j.DirA) + li * Math.PI * 0.25 + Math.PI * 0.125);
			SpawnLamp(Key(ta.Id, 0), c + lo * (R - 5.0) + Vector(0, 6.4, 0), lo, j.Objects);
		}

		float railY = c[1] + DrezinaConst.RAIL_TOP_ABOVE_FLOOR - DrezinaSettings.Get().RailHeightOffset;
		float off;
		float dXA = ma.ClosestDistance(Vector(c[0], railY, c[2]), off);
		float dXB = mb.ClosestDistance(Vector(c[0], railY, c[2]), off);
		vector cr = Vector(c[0], railY, c[2]);

		if (j.Ring)
			BuildRing(j, ma, mb, dXA, dXB, cr, railY);
		else
			BuildWye(j, ma, mb, dXA, dXB, railY);
	}

	void BuildRing(DrezinaJunction j, DrezinaTrack ma, DrezinaTrack mb, float dXA, float dXB, vector cr, float railY)
	{
		DrezinaTrackManager tm = DrezinaTrackManager.Get();
		// кольцо: по часовой (вид сверху), замкнуто само на себя
		array<vector> ring = new array<vector>;
		for (int k = 0; k <= 36; k++)
		{
			vector rp = cr + ArmDir(k * Math.PI2 / 36.0) * JUNC_RING_R;
			rp[1] = railY;
			ring.Insert(rp);
		}
		array<ref DrezinaLink> rl = new array<ref DrezinaLink>;
		DrezinaLink l1 = new DrezinaLink();
		l1.End = 1;
		l1.ToTrack = -1;
		l1.ToD = 0;
		l1.MergeDir = 1;
		l1.Side = 0;
		rl.Insert(l1);
		DrezinaLink l0 = new DrezinaLink();
		l0.End = 0;
		l0.ToTrack = -1;
		l0.MergeDir = -1;
		l0.Side = 0;
		rl.Insert(l0);
		int ringId = tm.CreateServiceTrack(ring, "Кольцо развязки", rl);
		DrezinaTrack rt = tm.GetTrack(ringId);
		if (!rt)
			return;
		l0.ToD = rt.GetLength();

		array<vector> arms = new array<vector>;
		arms.Insert(j.DirA);
		arms.Insert(j.DirA * -1.0);
		arms.Insert(j.DirB);
		arms.Insert(j.DirB * -1.0);
		for (int ai = 0; ai < 4; ai++)
		{
			vector o = arms[ai];
			DrezinaTrack m = ma;
			float dX = dXA;
			vector mdir = j.DirA;
			if (ai >= 2)
			{
				m = mb;
				dX = dXB;
				mdir = j.DirB;
			}
			int sM = 1;
			if (vector.Dot(o, mdir) < 0)
				sM = -1;
			float dP = dX + sM * JUNC_ARM_R;
			vector P, pdir;
			m.GetPosDir(dP, P, pdir);
			for (int sg = -1; sg <= 1; sg += 2)
			{
				float aq = DirAngle(o) + sg * 50 * Math.DEG2RAD;
				vector Q = cr + ArmDir(aq) * JUNC_RING_R;
				Q[1] = railY;
				vector tr = Vector(Math.Cos(aq), 0, -Math.Sin(aq));    // касательная кольца по росту дистанции
				vector tq = tr;
				int mergeQ = 1;
				if (vector.Dot(tr, Q - P) < 0)
				{
					tq = tr * -1.0;
					mergeQ = -1;
				}
				array<vector> nodes = new array<vector>;
				ConnectorNodes(P, o * -1.0, Q, tq, railY, nodes);
				array<ref DrezinaLink> cl = new array<ref DrezinaLink>;
				DrezinaLink a = new DrezinaLink();
				a.End = 0;
				a.ToTrack = m.GetId();
				a.ToD = dP;
				a.MergeDir = sM;
				a.Side = SideSign(o * -1.0, P, nodes[3]);
				cl.Insert(a);
				DrezinaLink b = new DrezinaLink();
				b.End = 1;
				b.ToTrack = ringId;
				float offQ;
				b.ToD = rt.ClosestDistance(Q, offQ);
				b.MergeDir = mergeQ;
				b.Side = SideSign(tq * -1.0, Q, nodes[7]);
				cl.Insert(b);
				tm.CreateServiceTrack(nodes, "Съезд на кольцо", cl);
			}
		}
	}

	void BuildWye(DrezinaJunction j, DrezinaTrack ma, DrezinaTrack mb, float dXA, float dXB, float railY)
	{
		DrezinaTrackManager tm = DrezinaTrackManager.Get();
		int sB = 1;
		if (vector.Dot(j.DirA, j.DirB) < 0)
			sB = -1;
		// съезд 1: с A (до пересечения) на B (после), съезд 2: с B (до) на A (после)
		for (int n = 0; n < 2; n++)
		{
			DrezinaTrack m0 = ma;
			DrezinaTrack m1 = mb;
			float d0 = dXA - JUNC_WYE_L;
			float d1 = dXB + sB * JUNC_WYE_L;
			int s0 = 1;
			int s1 = sB;
			if (n == 1)
			{
				m0 = mb;
				m1 = ma;
				d0 = dXB - sB * JUNC_WYE_L;
				d1 = dXA + JUNC_WYE_L;
				s0 = sB;
				s1 = 1;
			}
			vector P, pd, Q, qd;
			m0.GetPosDir(d0, P, pd);
			m1.GetPosDir(d1, Q, qd);
			float fs0 = s0;
			float fs1 = s1;
			vector t0 = Flat(pd) * fs0;
			vector t1 = Flat(qd) * fs1;
			array<vector> nodes = new array<vector>;
			ConnectorNodes(P, t0, Q, t1, railY, nodes);
			array<ref DrezinaLink> cl = new array<ref DrezinaLink>;
			DrezinaLink a = new DrezinaLink();
			a.End = 0;
			a.ToTrack = m0.GetId();
			a.ToD = d0;
			a.MergeDir = -s0;
			a.Side = SideSign(t0, P, nodes[3]);
			cl.Insert(a);
			DrezinaLink b = new DrezinaLink();
			b.End = 1;
			b.ToTrack = m1.GetId();
			b.ToD = d1;
			b.MergeDir = s1;
			b.Side = SideSign(t1 * -1.0, Q, nodes[7]);
			cl.Insert(b);
			tm.CreateServiceTrack(nodes, "Съезд", cl);
		}
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
			// пересекает другую линию — пол на её уровне (если это не выше допустимого), чтобы получилась развязка
			foreach (int oid, DrezinaTunnelData ot : m_Tunnels)
			{
				// уровень другой линии годится, если над новой остаётся не меньше 4 м земли
				if (ot.Zone || ot.FloorY > floorY + depth - 4.0 || Math.AbsFloat(ot.FloorY - floorY) > 6.0)
					continue;
				vector cx, cdA, cdB;
				float cda, cdb;
				if (FirstCrossing(MakeSpline(route, vector.Zero, ot.FloorY), GetSpline(ot), cx, cda, cdb, cdA, cdB))
				{
					t.FloorY = ot.FloorY;
					DrezinaTrackManager.Notify(sender, "Линия пересекает метро #" + ot.Id + ": пол на его уровне для перехода.");
					break;
				}
			}
		}

		m_Tunnels.Set(t.Id, t);
		int jBefore = m_Junctions.Count();
		RespawnAll();
		Save();
		BroadcastAll();
		if (m_Junctions.Count() > jBefore)
			DrezinaTrackManager.Notify(sender, "Пересечений с другими линиями: " + (m_Junctions.Count() - jBefore) + " — построены залы со стрелками.");

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
			m_Generators.Remove(Key(delId, 0));
			m_Generators.Remove(Key(delId, 1));
			m_Lamps.Remove(Key(delId, 0));
			m_Lamps.Remove(Key(delId, 1));
			RespawnAll();
			Save();
			BroadcastAll();
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
		else if (cmd == "test")
		{
			// /metro test tunnel | curve | stairs [шаг_вниз] [шаг_вперёд] [блоков] | entrance | hall | clear
			string what = "tunnel";
			if (args.Count() >= 3)
				what = args[2];
			what.ToLower();
			array<string> nums = new array<string>;
			for (int ai = 3; ai < args.Count(); ai++)
				nums.Insert(args[ai]);
			VanillaTest(sender, admin, what, nums);
		}
		else if (cmd == "measure")
		{
			// /metro measure — замер ванильных подземных блоков Ливонии: размеры коробки модели в лог сервера
			MeasureVanilla(sender, here);
		}
		else if (cmd == "rebuild")
		{
			RespawnAll();
			DrezinaTrackManager.Notify(sender, "Метро пересоздано, пересечений со стрелками: " + m_Junctions.Count() + ".");
		}
		else
		{
			DrezinaTrackManager.Notify(sender, "/metro a | via | auto <м> | undo | b | info | build [under|zone] [глубина] | preset | del [id] | list | tp a|b|<id>|<x> <z> | rebuild | measure");
		}
	}

	// /rail start и /rail end: две точки — вход и выход, метро между ними строится само
	// (под землёй, если позволяет рельеф, иначе в локации за картой)
	void ServerStartEnd(PlayerIdentity sender, bool isStart)
	{
		Print("[Drezina] ServerStartEnd start=" + isStart);
		if (!sender)
			return;
		PlayerBase admin = PlayerBase.Cast(sender.GetPlayer());
		if (!admin)
		{
			Print("[Drezina] ServerStartEnd: no player");
			return;
		}
		if (!m_Drafts)
			m_Drafts = new map<string, ref DrezinaMetroDraft>;
		string uid = sender.GetPlainId();
		DrezinaMetroDraft draft = m_Drafts.Get(uid);
		if (!draft)
		{
			draft = new DrezinaMetroDraft();
			m_Drafts.Set(uid, draft);
		}
		if (!draft.Points)
			draft.Points = new array<vector>;
		Print("[Drezina] ServerStartEnd: draft ok, points=" + draft.Points.Count());
		draft.Admin = admin;
		vector here = admin.GetPosition();

		if (isStart)
		{
			draft.Points.Clear();
			draft.Points.Insert(here);
			draft.HasB = false;
			draft.AutoStep = 0;
			DrezinaTrackManager.Notify(sender, "Вход метро отмечен. Переместитесь к выходу и напишите /rail end");
			return;
		}

		if (!draft.HasA())
		{
			DrezinaTrackManager.Notify(sender, "Сначала /rail start на месте входа.");
			return;
		}
		draft.B = here;
		draft.HasB = true;
		Build(sender, draft, "auto", DrezinaSettings.Get().MetroDefaultDepth);
		m_Drafts.Remove(uid);
	}

	// Каждый блок на миг ставится в 60 м над игроком, меряется (ClippingInfo — коробка модели,
	// GetCollisionBox — коробка геометрии) и удаляется. Результат: строки [Drezina] MEASURE в логе сервера.
	void MeasureVanilla(PlayerIdentity sender, vector here)
	{
		array<string> types = {"Land_Underground_Tunnel_Single", "Land_Underground_Tunnel_Single_Left", "Land_Underground_Tunnel_Single_Right",
			"Land_Underground_Corridor_Main_Both", "Land_Underground_Corridor_Main_Left", "Land_Underground_Corridor_Main_Right",
			"Land_Underground_Corridor_Connector", "Land_Underground_Corridor_Connector_Inv",
			"Land_Underground_Storage_Big", "Land_Underground_Storage_Big_Vent", "Land_Underground_Storage_Workshop", "Land_Underground_Storage_Barracks",
			"Land_Underground_Storage_Ammo", "Land_Underground_Storage_Hospital", "Land_Underground_WaterReservoir", "Land_Underground_WaterMaintenance",
			"Land_Underground_Floor_Comms", "Land_Underground_Floor_Crew",
			"Land_Underground_Stairs_Start", "Land_Underground_Stairs_Block", "Land_Underground_Stairs_Block_Corridor",
			"Land_Underground_Stairs_Block_Corridor_NoDoor", "Land_Underground_Stairs_Block_Terminator", "Land_Underground_Stairs_Exit",
			"Land_Underground_Entrance"};
		vector pos = here + Vector(0, 60, 0);
		int ok = 0;
		foreach (string type : types)
		{
			Object o = GetGame().CreateObjectEx(type, pos, ECE_SETUP | ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN | ECE_NOLIFETIME | ECE_NOPERSISTENCY_WORLD, RF_DEFAULT);
			if (!o)
			{
				Print("[Drezina] MEASURE " + type + ": НЕ СОЗДАН");
				continue;
			}
			o.SetPosition(pos);
			o.SetOrientation("0 0 0");
			vector clip[2];
			float r = o.ClippingInfo(clip);
			vector cb[2];
			bool hasCb = o.GetCollisionBox(cb);
			vector csize = clip[1] - clip[0];
			string line = "[Drezina] MEASURE " + type + " clip min=" + clip[0].ToString() + " max=" + clip[1].ToString() + " size=" + csize.ToString() + " r=" + r;
			if (hasCb)
			{
				vector gsize = cb[1] - cb[0];
				line += " coll min=" + cb[0].ToString() + " max=" + cb[1].ToString() + " size=" + gsize.ToString();
			}
			Print(line);
			GetGame().ObjectDelete(o);
			ok++;
		}
		DrezinaTrackManager.Notify(sender, "Замер готов: " + ok + " из " + types.Count() + " блоков. Пришлите строки [Drezina] MEASURE из script_*.log сервера.");
	}

	// ================================================================== ванильные блоки: тестовые сборки
	//
	// Размеры по замеру (/metro measure): Tunnel_Single — 10 м, центр модели в середине; Tunnel_Single_Left /
	// _Right — начало модели у входного торца, поворот на 30° (ось R ~18.5 м: вперёд 9.24, вбок 2.48);
	// Storage_Big — зал 15.5 x 20.9 м (торцы по оси Z: -10.45 / +10.42).

	static const float V_STRAIGHT = 10.0;
	static const float V_CURVE_ANG = 30.0;
	static const float V_CURVE_R = 18.47;
	static const float V_HALL_BACK = 10.45;
	static const float V_HALL_FRONT = 10.42;

	ref array<Object> m_TestObjects = new array<Object>;

	Object TestSpawn(string type, vector pos, vector dir)
	{
		Object o = DrezinaTrackManager.SpawnStatic(type, pos, dir);
		if (o)
			m_TestObjects.Insert(o);
		else
			Print("[Drezina] test: не создан " + type);
		return o;
	}

	// кусок тоннеля: 'S' прямой, 'L' / 'R' поворот на 30°; cur и h — начало куска и направление, сдвигаются на конец
	void PlaceVanillaPiece(string kind, inout vector cur, inout vector h, array<Object> outObjs)
	{
		vector side = Side(h);       // вправо
		if (kind == "S")
		{
			Object s1 = DrezinaTrackManager.SpawnStatic("Land_Underground_Tunnel_Single", cur + h * (V_STRAIGHT * 0.5), h);
			if (s1)
				outObjs.Insert(s1);
			cur = cur + h * V_STRAIGHT;
			return;
		}
		float a = V_CURVE_ANG * Math.DEG2RAD;
		float sg = 1;
		string type = "Land_Underground_Tunnel_Single_Right";
		if (kind == "L")
		{
			sg = -1;
			type = "Land_Underground_Tunnel_Single_Left";
		}
		Object c1 = DrezinaTrackManager.SpawnStatic(type, cur, h);
		if (c1)
			outObjs.Insert(c1);
		cur = cur + h * (V_CURVE_R * Math.Sin(a)) + side * (sg * V_CURVE_R * (1 - Math.Cos(a)));
		h = (h * Math.Cos(a) + side * (sg * Math.Sin(a))).Normalized();
	}

	void VanillaTest(PlayerIdentity sender, PlayerBase admin, string what, array<string> nums)
	{
		if (what == "clear")
		{
			foreach (Object o : m_TestObjects)
			{
				if (o)
					GetGame().ObjectDelete(o);
			}
			m_TestObjects.Clear();
			DrezinaTrackManager.Notify(sender, "Тестовые блоки убраны.");
			return;
		}
		vector here = admin.GetPosition();
		vector h = Flat(admin.GetDirection());
		// в воздухе на 25 м над землёй перед игроком — удобно облететь и посмотреть стыки
		vector base = here + h * 20.0;
		base[1] = GetGame().SurfaceY(base[0], base[2]) + 25.0;
		int before = m_TestObjects.Count();

		if (what == "tunnel" || what == "curve")
		{
			// зал — 2 прямых — поворот влево — 2 прямых — поворот вправо — 2 прямых — зал
			vector cur = base;
			if (what == "tunnel")
				TestSpawn("Land_Underground_Storage_Big", cur - h * V_HALL_FRONT, h);
			string seq = "SSLSSRSS";
			if (what == "curve")
				seq = "SLLLS";
			for (int i = 0; i < seq.Length(); i++)
				PlaceVanillaPiece(seq.Get(i), cur, h, m_TestObjects);
			if (what == "tunnel")
				TestSpawn("Land_Underground_Storage_Big", cur + h * V_HALL_BACK, h);
		}
		else if (what == "stairs")
		{
			// лестница: Start, N блоков со сдвигом (вниз, вперёд), внизу Block_Corridor
			float dy = 3.3;
			float dz = 0.0;
			int n = 3;
			if (nums.Count() > 0)
				dy = nums[0].ToFloat();
			if (nums.Count() > 1)
				dz = nums[1].ToFloat();
			if (nums.Count() > 2)
				n = nums[2].ToInt();
			TestSpawn("Land_Underground_Stairs_Start", base, h);
			vector sp = base;
			for (int k = 1; k <= n; k++)
			{
				sp = base - Vector(0, dy * k, 0) + h * (dz * k);
				TestSpawn("Land_Underground_Stairs_Block", sp, h);
			}
			TestSpawn("Land_Underground_Stairs_Block_Corridor", sp - Vector(0, dy, 0) + h * dz, h);
		}
		else if (what == "entrance")
		{
			vector ep = here + h * 25.0;
			ep[1] = GetGame().SurfaceY(ep[0], ep[2]);
			TestSpawn("Land_Underground_Entrance", ep, h);
		}
		else if (what == "hall")
		{
			TestSpawn("Land_Underground_Storage_Big", base, h);
			TestSpawn("Land_Underground_Corridor_Connector", base + h * (V_HALL_FRONT + 6.65), h);
			TestSpawn("Land_Underground_Corridor_Main_Both", base + h * (V_HALL_FRONT + 13.3 + 11.55), h);
		}
		DrezinaTrackManager.Notify(sender, "Тест «" + what + "»: поставлено " + (m_TestObjects.Count() - before) + " блоков (в 25 м над землёй впереди). Убрать: /metro test clear");
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

// Пересечение двух линий метро (зал со стрелками). Пересчитывается при запуске и после постройки/удаления.
class DrezinaJunction
{
	int A;
	int B;
	vector Center;     // y — пол
	vector DirA;       // направления осей линий в точке пересечения (по росту дистанции, горизонтально)
	vector DirB;
	bool Ring;         // кольцо (угол >= 55°) или два съезда
	float Radius;
	ref array<Object> Objects = new array<Object>;
}
