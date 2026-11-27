// Данные трассы (то, что хранится в tracks.json) и её геометрия.
// Геометрия строится одинаково на сервере и на клиенте из одних и тех же узлов,
// поэтому клиент может сам плавно двигать дрезину по синхронизированной дистанции.

class DrezinaTrackData
{
	int Id;
	string Name;
	ref array<vector> Nodes = new array<vector>; // точки, поставленные админом
	bool Service;                                // служебный путь развязки метро: без терминалов, не сохраняется
	int NoDispenser;                             // без терминала выдачи: 1 — у начала, 2 — у конца (концы, подключённые к другой линии)
	ref array<ref DrezinaLink> Links = new array<ref DrezinaLink>; // концы этого пути, примыкающие к другим путям
}

// Примыкание конца служебного пути (End: 0 — начало, 1 — конец) к точке ToD другого пути ToTrack.
// Доехав по этому пути до конца, дрезина переходит на ToTrack и едет в сторону MergeDir (+1 — к росту дистанции).
// И наоборот: едущая по ToTrack в сторону -MergeDir через точку ToD с рулём в сторону Side (+1 вправо,
// -1 влево по ходу) уходит на этот путь. Side = 0 — примыкание без стрелки (замыкание кольца).
class DrezinaLink
{
	int End;
	int ToTrack;
	float ToD;
	int MergeDir;
	int Side;
}

// Стрелка на пути (строится из примыканий служебных путей, на сервере и на клиенте одинаково)
class DrezinaSwitch
{
	float D;          // где на этом пути
	int Dir;          // в какую сторону надо ехать, чтобы уйти на ветку (+1 / -1 по дистанции)
	int Side;         // руль: +1 вправо, -1 влево
	int Branch;       // id служебного пути
	int BranchEnd;    // с какого его конца въезжаем (0 / 1)
}

class DrezinaTracksDB
{
	int Version = 1;
	ref array<ref DrezinaTrackData> Tracks = new array<ref DrezinaTrackData>;
}

class DrezinaTrack
{
	ref DrezinaTrackData m_Data;

	ref array<vector> m_Points = new array<vector>; // сглаженная линия
	ref array<ref DrezinaSwitch> m_Switches = new array<ref DrezinaSwitch>; // стрелки на этом пути
	ref array<float>  m_Cum    = new array<float>;  // накопленная длина до точки i
	float m_Length;

	void DrezinaTrack(DrezinaTrackData data)
	{
		m_Data = data;
		Build();
	}

	int GetId()
	{
		return m_Data.Id;
	}

	float GetLength()
	{
		return m_Length;
	}

	// Catmull-Rom через узлы админа, шаг ~SPLINE_STEP.
	void Build()
	{
		m_Points.Clear();
		m_Cum.Clear();
		m_Length = 0;

		array<vector> n = m_Data.Nodes;
		int count = n.Count();
		if (count == 0)
			return;

		if (count == 1)
		{
			m_Points.Insert(n[0]);
			m_Cum.Insert(0);
			return;
		}

		m_Points.Insert(n[0]);
		for (int i = 0; i < count - 1; i++)
		{
			vector p0 = n[Math.Max(i - 1, 0)];
			vector p1 = n[i];
			vector p2 = n[i + 1];
			vector p3 = n[Math.Min(i + 2, count - 1)];

			float segLen = vector.Distance(p1, p2);
			int steps = Math.Ceil(segLen / DrezinaConst.SPLINE_STEP);
			if (steps < 1)
				steps = 1;
			for (int s = 1; s <= steps; s++)
			{
				float t = s;
				t = t / steps; // без этого было бы целочисленное деление
				m_Points.Insert(CatmullRom(p0, p1, p2, p3, t));
			}
		}
		RemoveLoops();

		m_Cum.Insert(0);
		for (int k = 1; k < m_Points.Count(); k++)
		{
			m_Length += vector.Distance(m_Points[k - 1], m_Points[k]);
			m_Cum.Insert(m_Length);
		}
	}

	// Кривая через близкие узлы с резким поворотом даёт маленькую петлю (путь возвращается назад и снова
	// вперёд) — дрезину на ней разворачивало на 180°. Выкидываем точки, которые идут назад относительно
	// последнего направления (по горизонтали), пока линия снова не уйдёт вперёд.
	void RemoveLoops()
	{
		if (m_Points.Count() < 3)
			return;
		array<vector> q = new array<vector>;
		q.Insert(m_Points[0]);
		q.Insert(m_Points[1]);
		int dropped = 0;
		for (int k = 2; k < m_Points.Count(); k++)
		{
			vector p = m_Points[k];
			vector a = q[q.Count() - 1] - q[q.Count() - 2];
			vector b = p - q[q.Count() - 1];
			a[1] = 0;
			b[1] = 0;
			bool last = k == m_Points.Count() - 1;
			if (b.Length() < 0.02 && !last)
			{
				dropped++;
				continue;
			}
			if (a.Length() > 0.001 && vector.Dot(a.Normalized(), b.Normalized()) < -0.2)
			{
				dropped++;
				continue;            // точка позади — часть петли
			}
			q.Insert(p);
		}
		if (dropped > 0)
		{
			Print("[Drezina] путь #" + m_Data.Id + ": убрана петля/излом назад, точек " + dropped);
			m_Points.Clear();
			foreach (vector v : q)
				m_Points.Insert(v);
		}
	}

	static vector CatmullRom(vector p0, vector p1, vector p2, vector p3, float t)
	{
		float t2 = t * t;
		float t3 = t2 * t;
		vector r = (p1 * 2.0) + (p2 - p0) * t + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2 + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3;
		return r * 0.5;
	}

	// Позиция и направление (вдоль роста дистанции) в точке d.
	void GetPosDir(float d, out vector pos, out vector dir)
	{
		int cnt = m_Points.Count();
		if (cnt == 0)
		{
			pos = vector.Zero;
			dir = "0 0 1";
			return;
		}
		if (cnt == 1)
		{
			pos = m_Points[0];
			dir = "0 0 1";
			return;
		}

		d = Math.Clamp(d, 0, m_Length);

		// бинарный поиск отрезка
		int lo = 0;
		int hi = cnt - 1;
		while (hi - lo > 1)
		{
			int mid = (lo + hi) / 2;
			if (m_Cum[mid] <= d)
				lo = mid;
			else
				hi = mid;
		}

		float segLen = m_Cum[hi] - m_Cum[lo];
		float f = 0;
		if (segLen > 0.0001)
			f = (d - m_Cum[lo]) / segLen;

		pos = m_Points[lo] + (m_Points[hi] - m_Points[lo]) * f;
		dir = vector.Direction(m_Points[lo], m_Points[hi]).Normalized();
	}

	// Ближайшая к точке дистанция по пути и расстояние до неё.
	float ClosestDistance(vector p, out float outDist)
	{
		float best = 1000000000.0;
		float bestD = 0;
		for (int i = 0; i < m_Points.Count(); i++)
		{
			float dd = vector.DistanceSq(p, m_Points[i]);
			if (dd < best)
			{
				best = dd;
				bestD = m_Cum[i];
			}
		}
		outDist = Math.Sqrt(best);
		return bestD;
	}

	// Сериализация для RPC (узлов достаточно, геометрия строится на клиенте).
	static void Write(ParamsWriteContext ctx, DrezinaTrackData data)
	{
		ctx.Write(data.Id);
		ctx.Write(data.Name);
		int c = data.Nodes.Count();
		ctx.Write(c);
		for (int i = 0; i < c; i++)
			ctx.Write(data.Nodes[i]);
		ctx.Write(data.Service);
		int lc = data.Links.Count();
		ctx.Write(lc);
		foreach (DrezinaLink l : data.Links)
		{
			ctx.Write(l.End);
			ctx.Write(l.ToTrack);
			ctx.Write(l.ToD);
			ctx.Write(l.MergeDir);
			ctx.Write(l.Side);
		}
	}

	static DrezinaTrackData Read(ParamsReadContext ctx)
	{
		DrezinaTrackData data = new DrezinaTrackData();
		if (!ctx.Read(data.Id))
			return null;
		if (!ctx.Read(data.Name))
			return null;
		int c;
		if (!ctx.Read(c))
			return null;
		for (int i = 0; i < c; i++)
		{
			vector v;
			if (!ctx.Read(v))
				return null;
			data.Nodes.Insert(v);
		}
		if (!ctx.Read(data.Service))
			return null;
		int lc;
		if (!ctx.Read(lc))
			return null;
		for (int k = 0; k < lc; k++)
		{
			DrezinaLink l = new DrezinaLink();
			if (!ctx.Read(l.End) || !ctx.Read(l.ToTrack) || !ctx.Read(l.ToD) || !ctx.Read(l.MergeDir) || !ctx.Read(l.Side))
				return null;
			data.Links.Insert(l);
		}
		return data;
	}

	// примыкание у конца end (0 / 1) или null
	DrezinaLink LinkAt(int end)
	{
		foreach (DrezinaLink l : m_Data.Links)
		{
			if (l.End == end)
				return l;
		}
		return null;
	}

	bool IsService()
	{
		return m_Data.Service;
	}

	// есть стрелка съезда у самого конца end (до 1 м) — к этому концу можно подъезжать вплотную
	bool SwitchNearEnd(int end)
	{
		float e = 0;
		if (end == 1)
			e = GetLength();
		foreach (DrezinaSwitch sw : m_Switches)
		{
			if (Math.AbsFloat(sw.D - e) < 1.0)
				return true;
		}
		return false;
	}
}
