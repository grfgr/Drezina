// Данные метро для карт других модов (КПК и т.п.). Работает на клиенте: линии, входы и пересечения
// приходят с сервера (DrezinaRPC.TUNNELS_FULL). Другой мод подключает это через #ifdef DREZINA.
//
//   array<ref array<vector>> lines = new array<ref array<vector>>;
//   array<vector> entrances = new array<vector>;
//   DrezinaMetroMap.Collect(lines, entrances);
//
// lines     — линия каждого тоннеля на поверхности: точки через ~step метров (сглаженный маршрут);
// entrances — входы (головы бункеров) на поверхности, по два на тоннель.
//
// Подробно (для списка линий в админском КПК):
//
//   array<ref DrezinaMetroLine> info = new array<ref DrezinaMetroLine>;
//   array<ref DrezinaMetroCross> cross = new array<ref DrezinaMetroCross>;
//   DrezinaMetroMap.CollectFull(info, cross);

// одна линия метро
class DrezinaMetroLine
{
	int Id;
	bool Zone;                 // тоннель «в локации за картой» (входы всё равно там, где их поставили)
	float Length;              // длина по оси, м
	vector A;                  // начало (вход A) на поверхности
	vector B;                  // конец (вход B)
	int JoinA;                 // конец A подключён Т-развязкой к линии JoinA (станции нет), 0 — станция
	int JoinB;
	ref array<vector> Points = new array<vector>;   // ось на поверхности через ~step м
}

// пересечение линий (зал развязки)
class DrezinaMetroCross
{
	int A;                     // основная линия
	int B;                     // вторая линия (для Т-развязки — та, что подключена концом)
	vector Pos;                // центр зала на поверхности (y = 0)
	bool Tee;                  // Т-развязка (конец B примыкает к A)
	bool Ring;                 // кольцо (пересечение под большим углом)
}

class DrezinaMetroMap
{
	// растёт при каждом приходе данных метро с сервера: другой мод по нему видит, что пора перечитать
	static int s_Version;

	// клиент: удалить линию (как /metro del <id>). Сервер проверяет права админа Drezina
	// (admins.json / суперадмины VPP); после удаления всем клиентам приходят новые данные.
	static void RequestDelete(int id)
	{
		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		if (!player || id <= 0)
			return;
		GetGame().RPCSingleParam(player, DrezinaRPC.ADMIN_COMMAND, new Param1<string>(DrezinaConst.METRO_PREFIX + " del " + id), true);
	}

	protected static array<ref DrezinaTunnelData> Source()
	{
		DrezinaTunnelManager tm = DrezinaTunnelManager.Get();
		array<ref DrezinaTunnelData> src = tm.m_ClientTunnels;
		// одиночная игра / сервер: берём свои данные
		if (src.Count() == 0 && tm.m_Tunnels.Count() > 0)
		{
			src = new array<ref DrezinaTunnelData>;
			foreach (int id, DrezinaTunnelData td : tm.m_Tunnels)
				src.Insert(td);
		}
		return src;
	}

	static void Collect(array<ref array<vector>> lines, array<vector> entrances, float step = 20.0)
	{
		array<ref DrezinaMetroLine> full = new array<ref DrezinaMetroLine>;
		array<ref DrezinaMetroCross> cross = new array<ref DrezinaMetroCross>;
		CollectFull(full, cross, step);
		foreach (DrezinaMetroLine l : full)
		{
			lines.Insert(l.Points);
			entrances.Insert(l.A);
			entrances.Insert(l.B);
		}
	}

	static void CollectFull(array<ref DrezinaMetroLine> lines, array<ref DrezinaMetroCross> crosses, float step = 20.0)
	{
		array<ref DrezinaTunnelData> src = Source();
		foreach (DrezinaTunnelData t : src)
		{
			if (!t || t.Route.Count() < 2)
				continue;
			DrezinaTrack s = DrezinaTunnelManager.MakeSpline(t.Route, vector.Zero, 0);
			DrezinaMetroLine l = new DrezinaMetroLine();
			l.Id = t.Id;
			l.Zone = t.Zone;
			l.JoinA = t.JoinA;
			l.JoinB = t.JoinB;
			l.A = t.Route[0];
			l.B = t.Route[t.Route.Count() - 1];
			l.Length = s.GetLength();
			float d = 0;
			while (d < l.Length)
			{
				vector p, dir;
				s.GetPosDir(d, p, dir);
				l.Points.Insert(p);
				d += step;
			}
			vector pe, de;
			s.GetPosDir(l.Length, pe, de);
			l.Points.Insert(pe);
			lines.Insert(l);
		}

		DrezinaTunnelManager tm = DrezinaTunnelManager.Get();
		if (tm.m_ClientJunctions.Count() > 0)
		{
			foreach (DrezinaJunction cj : tm.m_ClientJunctions)
				crosses.Insert(MakeCross(cj, cj.Center));
		}
		else
		{
			// одиночная игра / сервер: свои залы, центр переводим на поверхность
			foreach (DrezinaJunction sj : tm.m_Junctions)
			{
				vector c = sj.Center;
				DrezinaTunnelData ta = tm.m_Tunnels.Get(sj.A);
				if (ta)
					c = Vector(c[0] - ta.Offset[0], 0, c[2] - ta.Offset[2]);
				crosses.Insert(MakeCross(sj, c));
			}
		}
	}

	protected static DrezinaMetroCross MakeCross(DrezinaJunction j, vector pos)
	{
		DrezinaMetroCross x = new DrezinaMetroCross();
		x.A = j.A;
		x.B = j.B;
		x.Pos = Vector(pos[0], 0, pos[2]);
		x.Tee = j.Tee;
		x.Ring = j.Ring;
		return x;
	}
}
