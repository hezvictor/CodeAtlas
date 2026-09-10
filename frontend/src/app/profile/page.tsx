"use client";
import { FormEvent, useEffect, useState } from "react";
import Navbar from "../../components/Navbar";
import { API, apiFetch, getToken, User } from "../../lib/auth";

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const notify = (text: string, failed = false) => { setMessage(failed ? "" : text); setError(failed ? text : ""); };
  useEffect(() => {
    if (!getToken()) { location.href = "/auth/login"; return; }
    apiFetch(`${API}/users/me`, { headers: { Authorization: `Bearer ${getToken()}` } }).then((r) => r.json()).then(setUser).catch((e) => notify(e.message, true));
  }, []);
  async function saveProfile(e: FormEvent<HTMLFormElement>) { e.preventDefault(); try { const r = await apiFetch(`${API}/users/me`, { method: "PATCH", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))) }); setUser(await r.json()); notify("个人资料已保存"); } catch (e) { notify(e instanceof Error ? e.message : "资料保存失败", true); } }
  async function changePassword(e: FormEvent<HTMLFormElement>) { e.preventDefault(); try { await apiFetch(`${API}/users/me/password`, { method: "PATCH", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(new FormData(e.currentTarget))) }); e.currentTarget.reset(); notify("旧密码验证通过，密码已修改"); } catch (e) { notify(e instanceof Error ? e.message : "旧密码错误，密码未修改", true); } }
  async function uploadAvatar(e: FormEvent<HTMLFormElement>) { e.preventDefault(); const file = (e.currentTarget.elements.namedItem("file") as HTMLInputElement).files?.[0]; if (!file) return; const body = new FormData(); body.append("file", file); try { const r = await apiFetch(`${API}/users/me/avatar`, { method: "POST", headers: { Authorization: `Bearer ${getToken()}` }, body }); setUser(await r.json()); notify("头像已更新"); } catch (e) { notify(e instanceof Error ? e.message : "头像上传失败", true); } }
  if (!user) return <><Navbar /><main className="workspace"><p>{error || "加载中..."}</p></main></>;
  const avatar = preview || user.avatar_url;
  return <><Navbar /><main className="workspace profile-page"><h1 className="page-title">个人中心</h1><section className="panel profile-card"><div className="profile profile-avatar">{avatar ? <img src={avatar} alt="头像" /> : user.nickname.slice(0, 1)}</div><div><strong>{user.nickname}</strong><p>{user.email}</p><small>注册于 {new Date(user.created_at).toLocaleDateString("zh-CN")}</small></div></section><form className="panel profile-form" onSubmit={saveProfile}><h3>个人信息</h3><label>昵称</label><input name="nickname" defaultValue={user.nickname} maxLength={80} required /><label>邮箱</label><input name="email" type="email" defaultValue={user.email} required /><button className="pill fill">保存资料</button></form><form className="panel profile-form" onSubmit={uploadAvatar}><h3>修改头像</h3><input name="file" type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => { const file = e.target.files?.[0]; if (file) setPreview(URL.createObjectURL(file)); }} required /><button className="pill">上传头像</button></form><form className="panel profile-form" onSubmit={changePassword}><h3>修改密码</h3><label>旧密码</label><input name="current_password" type="password" placeholder="请输入旧密码" required /><label>新密码</label><input name="new_password" type="password" placeholder="至少 8 位" minLength={8} required /><button className="pill fill">验证旧密码并修改</button></form>{message && <div className="toast success" role="status">{message}</div>}{error && <div className="toast error" role="alert">{error}</div>}</main></>;
}
