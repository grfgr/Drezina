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
			SpawnTunnel(t);
		}
		Print("[Drezina] loaded tunnels: " + m_Tunnels.Count());
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
		BroadcastAll();

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
