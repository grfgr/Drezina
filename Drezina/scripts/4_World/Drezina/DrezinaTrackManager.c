// Менеджер путей: хранение, спавн рельсов и станций выдачи, синхронизация с клиентами,
// команды админа (/rail ...). Существует и на сервере, и на клиенте (на клиенте — только геометрия).

class DrezinaDraft
{
	PlayerBase m_Admin;
	ref array<vector> m_Nodes = new array<vector>;
	ref array<Object> m_Preview = new array<Object>;
	float m_AutoStep;   // 0 = выключено
	int m_EditTrackId;  // 0 = новая трасса, иначе редактирование существующей (продление)
}

class DrezinaTrackManager extends Managed
{
	static ref DrezinaTrackManager s_Instance;

	ref map<int, ref DrezinaTrack> m_Tracks = new map<int, ref DrezinaTrack>;
	ref map<int, ref array<Object>> m_WorldObjects = new map<int, ref array<Object>>; // рельсы + станции, только сервер
	ref array<Drezina_Handcar> m_Handcars = new array<Drezina_Handcar>;
	ref map<string, ref DrezinaDraft> m_Drafts = new map<string, ref DrezinaDraft>;  // по Steam ID админа

	static DrezinaTrackManager Get()
	{
		if (!s_Instance)
			s_Instance = new DrezinaTrackManager();
		return s_Instance;
	}

	DrezinaTrack GetTrack(int id)
	{
		return m_Tracks.Get(id);
	}

	// ------------------------------------------------------------------ сервер: запуск / сохранение

	void ServerInit()
	{
		DrezinaSettings.Load();
		DrezinaAdmins.Load();
		LoadTracks();
		GetGame().GetCallQueue(CALL_CATEGORY_GAMEPLAY).CallLater(ServerTick, 250, true);
	}

	void LoadTracks()
	{
		DrezinaTracksDB db = new DrezinaTracksDB();
		if (FileExist(DrezinaConst.TRACKS_FILE))
			JsonFileLoader<DrezinaTracksDB>.JsonLoadFile(DrezinaConst.TRACKS_FILE, db);

		foreach (DrezinaTrackData data : db.Tracks)
		{
			if (!data || data.Nodes.Count() < 2)
				continue;
			DrezinaTrack t = new DrezinaTrack(data);
			m_Tracks.Set(data.Id, t);
			SpawnTrackObjects(t);
		}
		Print("[Drezina] loaded tracks: " + m_Tracks.Count());
	}

	void SaveTracks()
	{
		if (!FileExist(DrezinaConst.PROFILE_DIR))
			MakeDirectory(DrezinaConst.PROFILE_DIR);

		DrezinaTracksDB db = new DrezinaTracksDB();
		foreach (int id, DrezinaTrack t : m_Tracks)
			db.Tracks.Insert(t.m_Data);
		JsonFileLoader<DrezinaTracksDB>.JsonSaveFile(DrezinaConst.TRACKS_FILE, db);
	}

	int NextTrackId()
	{
		int maxId = 0;
		foreach (int id, DrezinaTrack t : m_Tracks)
		{
			if (id > maxId)
				maxId = id;
		}
		return maxId + 1;
	}

	// ------------------------------------------------------------------ сервер: объекты мира

	static Object SpawnStatic(string type, vector pos, vector dir)
	{
		int flags = ECE_SETUP | ECE_CREATEPHYSICS | ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN | ECE_NOLIFETIME | ECE_NOPERSISTENCY_WORLD;
		Object obj = GetGame().CreateObjectEx(type, pos, flags, RF_DEFAULT);
		if (obj)
		{
			obj.SetPosition(pos);
			obj.SetDirection(dir);
			// коллизия статического объекта не поворачивается вместе с моделью:
			// повторно применить ориентацию и обновить (так же делает экспорт DayZ Editor)
			obj.SetOrientation(obj.GetOrientation());
			obj.Update();
		}
		return obj;
	}

	// Рельсы: на прямых участках звенья по 10 м (меньше объектов), на кривых — по 2 м.
	void SpawnRails(DrezinaTrack t, array<Object> outObjects)
	{
		float len = t.GetLength();
		if (len < 0.1)
			return;
		vector up = Vector(0, DrezinaSettings.Get().RailHeightOffset, 0);
		float d = 0;
		while (d < len - 0.01)
		{
			string type = "Drezina_Rail";
			float piece = DrezinaConst.RAIL_PIECE_LEN;
			if (d + 10.0 <= len && IsStraight(t, d, d + 10.0))
			{
				type = "Drezina_Rail10";
				piece = 10.0;
			}
			float center = d + piece * 0.5;
			if (center + piece * 0.5 > len)
				center = Math.Max(len - piece * 0.5, piece * 0.5); // последний кусок — с нахлёстом назад
			vector pos, dir;
			t.GetPosDir(center, pos, dir);
			Object rail = SpawnStatic(type, pos + up, dir);
			if (rail)
				outObjects.Insert(rail);
			d += piece;
		}
	}

	static bool IsStraight(DrezinaTrack t, float d0, float d1)
	{
		vector p0, dir0, p1, dir1, pm, dirm;
		t.GetPosDir(d0 + 0.01, p0, dir0);
		t.GetPosDir(d1 - 0.01, p1, dir1);
		t.GetPosDir((d0 + d1) * 0.5, pm, dirm);
		return vector.Dot(dir0, dir1) > 0.9995 && vector.Dot(dir0, dirm) > 0.9995;
	}

	void SpawnTrackObjects(DrezinaTrack t)
	{
		DespawnTrackObjects(t.GetId());

		array<Object> objs = new array<Object>;
		SpawnRails(t, objs);

		// Станции выдачи у обоих концов пути.
		SpawnDispenser(t, true, objs);
		SpawnDispenser(t, false, objs);

		m_WorldObjects.Set(t.GetId(), objs);
	}

	void SpawnDispenser(DrezinaTrack t, bool atStart, array<Object> objs)
	{
		DrezinaSettings st = DrezinaSettings.Get();
		float d = st.DispenserBackOffset;
		if (!atStart)
			d = t.GetLength() - st.DispenserBackOffset;

		vector pos, dir;
		t.GetPosDir(d, pos, dir);
		// всегда справа, если стоять у торца лицом в путь (на станции метро — со стороны,
		// противоположной платформе)
		vector side = Vector(dir[2], 0, -dir[0]).Normalized();
		if (!atStart)
			side = side * -1;
		vector dPos = pos + side * st.DispenserSideOffset;

		// Станция смотрит на путь.
		Drezina_Dispenser disp = Drezina_Dispenser.Cast(SpawnStatic("Drezina_Dispenser", dPos, side * -1));
		if (disp)
		{
			disp.m_TrackId = t.GetId();
			disp.m_AtStart = atStart;
			objs.Insert(disp);
		}
	}

	void DespawnTrackObjects(int id)
	{
		array<Object> objs = m_WorldObjects.Get(id);
		if (objs)
		{
			foreach (Object o : objs)
			{
				if (o)
					GetGame().ObjectDelete(o);
			}
		}
		m_WorldObjects.Remove(id);

		// Дрезины этого пути тоже убираем.
		for (int i = m_Handcars.Count() - 1; i >= 0; i--)
		{
			Drezina_Handcar hc = m_Handcars[i];
			if (hc && hc.m_TrackId == id)
			{
				hc.ServerClearDriver();
				GetGame().ObjectDelete(hc);
			}
		}
	}

	// ------------------------------------------------------------------ дрезины

	bool m_UpdateHooked;

	void RegisterHandcar(Drezina_Handcar hc)
	{
		if (m_Handcars.Find(hc) == -1)
			m_Handcars.Insert(hc);
		if (!m_UpdateHooked)
		{
			GetGame().GetUpdateQueue(CALL_CATEGORY_GAMEPLAY).Insert(OnUpdate);
			m_UpdateHooked = true;
		}
	}

	// каждый кадр (сервер и клиент): движение, анимация, звук и свет дрезин
	void OnUpdate(float timeslice)
	{
		for (int i = m_Handcars.Count() - 1; i >= 0; i--)
		{
			Drezina_Handcar hc = m_Handcars[i];
			if (hc && !hc.m_TickedByRide)
				hc.Tick(timeslice);
		}
	}

	void UnregisterHandcar(Drezina_Handcar hc)
	{
		int idx = m_Handcars.Find(hc);
		if (idx != -1)
			m_Handcars.Remove(idx);
	}

	int CountHandcarsOnTrack(int trackId)
	{
		int c = 0;
		foreach (Drezina_Handcar hc : m_Handcars)
		{
			if (hc && hc.m_TrackId == trackId)
				c++;
		}
		return c;
	}

	// Ближайшая свободная дрезина около точки пути.
	Drezina_Handcar FindIdleHandcarNear(int trackId, float dist, float radius)
	{
		foreach (Drezina_Handcar hc : m_Handcars)
		{
			if (hc && hc.m_TrackId == trackId && !hc.HasDriver() && Math.AbsFloat(hc.m_Dist - dist) <= radius)
				return hc;
		}
		return null;
	}

	// Есть ли впереди другая дрезина ближе clearance (для остановки).
	bool IsBlocked(Drezina_Handcar self, float newDist)
	{
		float clearance = DrezinaSettings.Get().HandcarClearance;
		foreach (Drezina_Handcar hc : m_Handcars)
		{
			if (!hc || hc == self || hc.m_TrackId != self.m_TrackId)
				continue;
			float gapNow = Math.AbsFloat(hc.m_Dist - self.m_Dist);
			float gapNew = Math.AbsFloat(hc.m_Dist - newDist);
			if (gapNew < clearance && gapNew < gapNow)
				return true;
		}
		return false;
	}

	// Взять дрезину на станции: свободная рядом — садимся в неё, иначе спавним новую.
	void ServerTakeHandcar(PlayerBase player, Drezina_Dispenser disp)
	{
		if (!disp)
		{
			Print("[Drezina] take: нет станции выдачи");
			return;
		}
		Print("[Drezina] take: станция выдачи пути #" + disp.m_TrackId + ", начало=" + disp.m_AtStart);
		ServerTakeAt(player, disp.m_TrackId, disp.m_AtStart);
	}

	// Выдать дрезину у конца пути (у станции выдачи или по команде /rail take).
	void ServerTakeAt(PlayerBase player, int trackId, bool atStart)
	{
		DrezinaTrack t = GetTrack(trackId);
		if (!player || !player.IsAlive())
			return;
		if (!t)
		{
			Print("[Drezina] take: путь #" + trackId + " не найден");
			Notify(player.GetIdentity(), "Путь #" + trackId + " не найден на сервере.");
			return;
		}
		if (player.m_DrezinaHandcar)
		{
			Notify(player.GetIdentity(), "Вы уже на дрезине.");
			return;
		}

		DrezinaSettings st = DrezinaSettings.Get();
		float startDist = st.HandcarClearance * 0.5 + 1.0;
		int dir = 1;
		if (!atStart)
		{
			startDist = t.GetLength() - startDist;
			dir = -1;
		}
		startDist = Math.Clamp(startDist, 0, t.GetLength());

		Drezina_Handcar hc = FindIdleHandcarNear(t.GetId(), startDist, 8.0);
		if (hc)
		{
			// свободная дрезина у станции — просто разворачиваем её от торца и садимся
			hc.ServerPlaceOnTrack(t.GetId(), hc.m_Dist, dir);
		}
		else
		{
			if (CountHandcarsOnTrack(t.GetId()) >= st.MaxHandcarsPerTrack)
			{
				Notify(player.GetIdentity(), "Все дрезины этого пути заняты. Подождите.");
				return;
			}

			foreach (Drezina_Handcar other : m_Handcars)
			{
				if (other && other.m_TrackId == t.GetId() && Math.AbsFloat(other.m_Dist - startDist) < st.HandcarClearance)
				{
					Notify(player.GetIdentity(), "Путь у станции занят другой дрезиной.");
					return;
				}
			}

			vector pos, tdir;
			t.GetPosDir(startDist, pos, tdir);
			int flags = ECE_CREATEPHYSICS | ECE_KEEPHEIGHT | ECE_NOSURFACEALIGN | ECE_NOLIFETIME | ECE_NOPERSISTENCY_WORLD;
			hc = Drezina_Handcar.Cast(GetGame().CreateObjectEx("Drezina_Handcar", pos, flags, RF_DEFAULT));
			if (!hc)
			{
				Print("[Drezina] take: !!! не удалось создать Drezina_Handcar");
				Notify(player.GetIdentity(), "Не удалось создать дрезину (см. лог сервера).");
				return;
			}
			Print("[Drezina] take: дрезина создана на " + pos);
			hc.ServerPlaceOnTrack(t.GetId(), startDist, dir);
		}

		// дрезина подана — встать за рычаг игрок решает сам (действие «Встать за рычаг»)
		Notify(player.GetIdentity(), "Дрезина подана на путь. Подойдите и выберите «Встать за рычаг».");
	}

	// ------------------------------------------------------------------ сервер: тик

	void ServerTick()
	{
		// авто-прокладка: добавляем узел, когда админ отошёл на шаг
		foreach (string uid, DrezinaDraft draft : m_Drafts)
		{
			if (!draft || draft.m_AutoStep <= 0 || !draft.m_Admin)
				continue;
			vector p = draft.m_Admin.GetPosition();
			int c = draft.m_Nodes.Count();
			if (c == 0 || vector.Distance(draft.m_Nodes[c - 1], p) >= draft.m_AutoStep)
			{
				draft.m_Nodes.Insert(p);
				RebuildPreview(draft);
			}
		}
	}

	// ------------------------------------------------------------------ синхронизация с клиентами

	// RPC отправляем «на объект игрока» — так их принимает PlayerBase.OnRPC на клиенте.
	void SendAllTo(PlayerIdentity identity)
	{
		if (!identity)
			return;
		Object target = identity.GetPlayer();
		if (!target)
			return;
		ScriptRPC rpc = new ScriptRPC();
		int c = m_Tracks.Count();
		rpc.Write(c);
		foreach (int id, DrezinaTrack t : m_Tracks)
			DrezinaTrack.Write(rpc, t.m_Data);
		rpc.Send(target, DrezinaRPC.TRACKS_FULL, true, identity);
	}

	void BroadcastTrack(DrezinaTrack t)
	{
		array<Man> players = new array<Man>;
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			if (!m || !m.GetIdentity())
				continue;
			ScriptRPC rpc = new ScriptRPC();
			DrezinaTrack.Write(rpc, t.m_Data);
			rpc.Send(m, DrezinaRPC.TRACK_ADD, true, m.GetIdentity());
		}
	}

	void BroadcastRemove(int id)
	{
		array<Man> players = new array<Man>;
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			if (!m || !m.GetIdentity())
				continue;
			ScriptRPC rpc = new ScriptRPC();
			rpc.Write(id);
			rpc.Send(m, DrezinaRPC.TRACK_REMOVE, true, m.GetIdentity());
		}
	}

	// Клиент: приём RPC (вызывается из DayZGame.OnRPC).
	bool ClientOnRPC(int rpc_type, ParamsReadContext ctx)
	{
		if (rpc_type == DrezinaRPC.TRACKS_FULL)
		{
			m_Tracks.Clear();
			int c;
			if (!ctx.Read(c))
				return true;
			for (int i = 0; i < c; i++)
			{
				DrezinaTrackData data = DrezinaTrack.Read(ctx);
				if (data)
					m_Tracks.Set(data.Id, new DrezinaTrack(data));
			}
			return true;
		}
		if (rpc_type == DrezinaRPC.TRACK_ADD)
		{
			DrezinaTrackData d2 = DrezinaTrack.Read(ctx);
			if (d2)
				m_Tracks.Set(d2.Id, new DrezinaTrack(d2));
			return true;
		}
		if (rpc_type == DrezinaRPC.TRACK_REMOVE)
		{
			int rid;
			if (ctx.Read(rid))
				m_Tracks.Remove(rid);
			return true;
		}
		return false;
	}

	// ------------------------------------------------------------------ команды админа

	// Сообщение игроку: всплывающее уведомление + строка в чате (уведомления бывают скрыты) + лог сервера.
	static void Notify(PlayerIdentity identity, string text)
	{
		Print("[Drezina] msg: " + text);
		if (!identity)
			return;
		NotificationSystem.SendNotificationToPlayerIdentityExtended(identity, 6, "Дрезина", text);
		Object target = identity.GetPlayer();
		if (target)
			GetGame().RPCSingleParam(target, DrezinaRPC.CHAT_MSG, new Param1<string>(text), true, identity);
	}

	void ServerOnAdminCommand(PlayerIdentity sender, string text)
	{
		if (!DrezinaAdmins.IsAdmin(sender))
		{
			Notify(sender, "Нет прав: ваш Steam ID не в admins.json");
			return;
		}
		PlayerBase admin = PlayerBase.Cast(sender.GetPlayer());
		if (!admin)
			return;

		text.TrimInPlace();
		array<string> args = new array<string>;
		text.Replace(",", " ");
		text.Split(" ", args);
		// убираем пустые
		for (int i = args.Count() - 1; i >= 0; i--)
		{
			if (args[i] == "")
				args.Remove(i);
		}
		string cmd = "help";
		if (args.Count() >= 2)
			cmd = args[1];
		cmd.ToLower();
		if (cmd == "delete")
			cmd = "del";

		// метро двумя точками: /rail start — вход здесь, телепорт, /rail end — выход и постройка
		if (cmd == "start" || cmd == "старт" || cmd == "end" || cmd == "энд" || cmd == "конец")
		{
			bool isStart = false;
			if (cmd == "start" || cmd == "старт")
				isStart = true;
			Print("[Drezina] cmd " + cmd + " isStart=" + isStart);
			DrezinaTunnelManager tm = DrezinaTunnelManager.Get();
			if (!tm)
			{
				Print("[Drezina] !!! DrezinaTunnelManager is null");
				return;
			}
			tm.ServerStartEnd(sender, isStart);
			return;
		}
		// проверка выдачи без будки: дрезина у ближайшего конца ближайшего пути
		if (cmd == "take")
		{
			vector tp = admin.GetPosition();
			int tid = FindNearestTrack(tp, 30.0);
			if (tid == 0)
			{
				Notify(sender, "Рядом (30 м) нет пути.");
				return;
			}
			DrezinaTrack tt = GetTrack(tid);
			vector a0, a1, dd;
			tt.GetPosDir(0, a0, dd);
			tt.GetPosDir(tt.GetLength(), a1, dd);
			ServerTakeAt(admin, tid, vector.Distance(tp, a0) <= vector.Distance(tp, a1));
			return;
		}

		string uid = sender.GetPlainId();
		DrezinaDraft draft = m_Drafts.Get(uid);
		vector here = admin.GetPosition();

		switch (cmd)
		{
			case "new":
			{
				if (draft)
					ClearPreview(draft);
				draft = new DrezinaDraft();
				draft.m_Admin = admin;
				draft.m_Nodes.Insert(here);
				m_Drafts.Set(uid, draft);
				RebuildPreview(draft);
				Notify(sender, "Новый путь начат. Ходите и пишите /rail add (или /rail auto 4). Закончить: /rail done");
				break;
			}
			case "extend":
			{
				// продолжить существующий путь от ближайшего к админу конца
				int extId = FindNearestTrack(here, 15.0);
				if (extId == 0)
				{
					Notify(sender, "Рядом (15 м) нет пути для продления.");
					break;
				}
				DrezinaTrack et = GetTrack(extId);
				if (draft)
					ClearPreview(draft);
				draft = new DrezinaDraft();
				draft.m_Admin = admin;
				draft.m_EditTrackId = extId;
				array<vector> en = et.m_Data.Nodes;
				if (vector.Distance(here, en[0]) < vector.Distance(here, en[en.Count() - 1]))
				{
					for (int r = en.Count() - 1; r >= 0; r--)
						draft.m_Nodes.Insert(en[r]);
				}
				else
				{
					draft.m_Nodes.InsertAll(en);
				}
				m_Drafts.Set(uid, draft);
				RebuildPreview(draft);
				Notify(sender, "Продление пути #" + extId + ". /rail add, /rail auto, затем /rail done");
				break;
			}
			case "add":
			{
				if (!draft)
				{
					Notify(sender, "Сначала /rail new");
					break;
				}
				draft.m_Nodes.Insert(here);
				RebuildPreview(draft);
				Notify(sender, "Точка " + draft.m_Nodes.Count() + " добавлена.");
				break;
			}
			case "auto":
			{
				if (!draft)
				{
					Notify(sender, "Сначала /rail new");
					break;
				}
				float step = 0;
				if (args.Count() >= 3)
					step = args[2].ToFloat();
				if (step > 0 && step < DrezinaSettings.Get().AutoNodeMinStep)
					step = DrezinaSettings.Get().AutoNodeMinStep;
				draft.m_AutoStep = step;
				draft.m_Admin = admin;
				if (step > 0)
					Notify(sender, "Авто-прокладка: точка каждые " + step + " м. Выключить: /rail auto 0");
				else
					Notify(sender, "Авто-прокладка выключена.");
				break;
			}
			case "undo":
			{
				if (draft && draft.m_Nodes.Count() > 1)
				{
					draft.m_Nodes.Remove(draft.m_Nodes.Count() - 1);
					RebuildPreview(draft);
					Notify(sender, "Последняя точка удалена.");
				}
				break;
			}
			case "cancel":
			{
				if (draft)
				{
					ClearPreview(draft);
					m_Drafts.Remove(uid);
				}
				Notify(sender, "Черновик отменён.");
				break;
			}
			case "done":
			{
				if (!draft || draft.m_Nodes.Count() < 2)
				{
					Notify(sender, "Нужно минимум 2 точки.");
					break;
				}
				ClearPreview(draft);
				DrezinaTrackData data;
				if (draft.m_EditTrackId != 0 && GetTrack(draft.m_EditTrackId))
				{
					data = GetTrack(draft.m_EditTrackId).m_Data;
					data.Nodes.Clear();
					data.Nodes.InsertAll(draft.m_Nodes);
				}
				else
				{
					data = new DrezinaTrackData();
					data.Id = NextTrackId();
					data.Name = "Путь " + data.Id;
					data.Nodes.InsertAll(draft.m_Nodes);
				}
				m_Drafts.Remove(uid);

				DrezinaTrack t = new DrezinaTrack(data);
				m_Tracks.Set(data.Id, t);
				SpawnTrackObjects(t);
				SaveTracks();
				BroadcastTrack(t);
				Notify(sender, "Путь #" + data.Id + " сохранён, длина " + Math.Round(t.GetLength()) + " м.");
				break;
			}
			case "del":
			{
				int delId = 0;
				if (args.Count() >= 3)
					delId = args[2].ToInt();
				else
					delId = FindNearestTrack(here, 15.0);
				if (delId == 0 || !GetTrack(delId))
				{
					Notify(sender, "Путь не найден (укажите номер или подойдите ближе 15 м).");
					break;
				}
				DespawnTrackObjects(delId);
				m_Tracks.Remove(delId);
				SaveTracks();
				BroadcastRemove(delId);
				Notify(sender, "Путь #" + delId + " удалён.");
				break;
			}
			case "list":
			{
				string msg = "";
				foreach (int lid, DrezinaTrack lt : m_Tracks)
					msg += "#" + lid + " " + Math.Round(lt.GetLength()) + "м; ";
				if (msg == "")
					msg = "Путей нет.";
				Notify(sender, msg);
				break;
			}
			case "tp":
			{
				int tpId = 0;
				if (args.Count() >= 3)
					tpId = args[2].ToInt();
				DrezinaTrack tpt = GetTrack(tpId);
				if (tpt)
				{
					vector tpPos, tpDir;
					tpt.GetPosDir(0, tpPos, tpDir);
					admin.SetPosition(tpPos + Vector(tpDir[2], 0, -tpDir[0]) * 1.5);
				}
				break;
			}
			case "reload":
			{
				foreach (int rid, DrezinaTrack rt : m_Tracks)
					DespawnTrackObjects(rid);
				m_Tracks.Clear();
				DrezinaSettings.Load();
				DrezinaAdmins.Load();
				LoadTracks();
				// разошлём всем заново
				array<Man> players = new array<Man>;
				GetGame().GetPlayers(players);
				foreach (Man m : players)
				{
					if (m && m.GetIdentity())
						SendAllTo(m.GetIdentity());
				}
				Notify(sender, "Перезагружено: " + m_Tracks.Count() + " путей.");
				break;
			}
			default:
			{
				Notify(sender, "/rail start (вход метро) -> /rail end (выход) | new | add | auto <м> | undo | done | cancel | extend | del [id] | list | tp <id> | take | reload");
				break;
			}
		}
	}

	// Создать путь из готовых узлов (используется метро).
	int CreateTrack(array<vector> nodes, string name)
	{
		DrezinaTrackData data = new DrezinaTrackData();
		data.Id = NextTrackId();
		data.Name = name;
		data.Nodes.InsertAll(nodes);
		DrezinaTrack t = new DrezinaTrack(data);
		m_Tracks.Set(data.Id, t);
		SpawnTrackObjects(t);
		SaveTracks();
		BroadcastTrack(t);
		return data.Id;
	}

	void DeleteTrack(int id)
	{
		if (!GetTrack(id))
			return;
		DespawnTrackObjects(id);
		m_Tracks.Remove(id);
		SaveTracks();
		BroadcastRemove(id);
	}

	int FindNearestTrack(vector p, float maxDist)
	{
		int bestId = 0;
		float best = maxDist;
		foreach (int id, DrezinaTrack t : m_Tracks)
		{
			float dist;
			t.ClosestDistance(p, dist);
			if (dist < best)
			{
				best = dist;
				bestId = id;
			}
		}
		return bestId;
	}

	// Черновик показываем настоящими рельсами, чтобы админ видел трассу.
	void RebuildPreview(DrezinaDraft draft)
	{
		ClearPreview(draft);
		if (draft.m_Nodes.Count() < 2)
			return;
		DrezinaTrackData tmp = new DrezinaTrackData();
		tmp.Nodes.InsertAll(draft.m_Nodes);
		DrezinaTrack t = new DrezinaTrack(tmp);
		SpawnRails(t, draft.m_Preview);
	}

	void ClearPreview(DrezinaDraft draft)
	{
		foreach (Object o : draft.m_Preview)
		{
			if (o)
				GetGame().ObjectDelete(o);
		}
		draft.m_Preview.Clear();
	}
}
