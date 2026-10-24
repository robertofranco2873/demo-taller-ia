import { Pencil, Trash2, UserPlus, Users } from "lucide-react";
import { useState } from "react";
import { DemoLock } from "../components/DemoLock";
import { Field, SelectField } from "../components/fields";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, Modal, Notice, PageHeader, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAppInfo } from "../lib/appInfo";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { ROLE_LABEL } from "../lib/modules";
import type { Role, Technician, User } from "../lib/types";

interface Form { id?: number; username: string; name: string; role: Role; technician_id: number | null; active: boolean; password: string }
const EMPTY: Form = { username: "", name: "", role: "recepcion", technician_id: null, active: true, password: "" };
// Usuarios de la semilla: en la demo pública no se les puede cambiar rol, contraseña ni desactivar.
const DEMO_USERNAMES = new Set(["gerente", "recepcion", "tecnico", "lucia", "miguel", "sofia"]);

export default function Usuarios() {
  const toast = useToast();
  const { user: me } = useAuth();
  const { demo_mode: demo } = useAppInfo();
  const { data, error, loading, reload } = useApi<{ users: User[] }>("/api/users");
  const techs = useApi<Technician[]>("/api/technicians");
  const [form, setForm] = useState<Form | null>(null);
  const [del, setDel] = useState<User | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (error) return <ErrorState message={error} onRetry={reload} />;

  async function save() {
    if (!form) return;
    setErr(null);
    try {
      if (form.id) {
        await api.put(`/api/users/${form.id}`, { name: form.name, role: form.role, technician_id: form.technician_id, active: form.active, password: form.password || null });
      } else {
        await api.post("/api/users", form);
      }
      toast("Usuario guardado.");
      setForm(null);
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function remove() {
    try {
      await api.del(`/api/users/${del!.id}`);
      toast("Usuario eliminado.");
      setDel(null);
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  return (
    <div>
      <PageHeader icon={Users} title="Usuarios" subtitle="Contraseñas con bcrypt; permisos por rol validados en el servidor"
        crumbs={[{ label: "Administración" }, { label: "Usuarios" }]}
        actions={<Button variant="primary" icon={UserPlus} onClick={() => { setErr(null); setForm(EMPTY); }}>Nuevo usuario</Button>} />
      <Card>
        <Table rows={data?.users} loading={loading} rowKey={(u) => u.id} columns={[
          { key: "u", header: "Usuario", render: (u) => <span className="font-medium text-text">@{u.username}</span> },
          { key: "n", header: "Nombre", render: (u) => u.name },
          { key: "r", header: "Rol", render: (u) => ROLE_LABEL[u.role] },
          { key: "t", header: "Técnico", hideOnMobile: true, render: (u) => u.technician ?? "—" },
          { key: "a", header: "Estado", render: (u) => (u.active ? <span className="text-success">Activo</span> : <span className="text-muted">Inactivo</span>) },
          { key: "x", header: "", render: (u) => (
            <span className="flex justify-end gap-1">
              <Button size="sm" variant="ghost" icon={Pencil} aria-label={`Editar ${u.username}`} onClick={() => { setErr(null); setForm({ id: u.id, username: u.username, name: u.name, role: u.role, technician_id: u.technician_id, active: !!u.active, password: "" }); }} />
              {u.id !== me?.id && <DemoLock><Button size="sm" variant="ghost" icon={Trash2} aria-label={`Eliminar ${u.username}`} onClick={() => setDel(u)} /></DemoLock>}
            </span>
          ) },
        ]} />
      </Card>

      <Modal open={!!form} onClose={() => setForm(null)} title={form?.id ? `Editar @${form.username}` : "Nuevo usuario"}>
        {form && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Usuario" value={form.username} disabled={!!form.id} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            <Field label="Nombre" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <DemoLock locked={demo && !!form.id && DEMO_USERNAMES.has(form.username)}>
              <div className="w-full">
                <SelectField label="Rol" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                  {(Object.keys(ROLE_LABEL) as Role[]).map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                </SelectField>
              </div>
            </DemoLock>
            {form.role === "tecnico" && (
              <SelectField label="Técnico ligado" value={form.technician_id ?? ""} onChange={(e) => setForm({ ...form, technician_id: Number(e.target.value) || null })}>
                <option value="">Elige…</option>
                {techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </SelectField>
            )}
            <DemoLock locked={demo && !!form.id}>
              <div className="w-full">
                <Field label={form.id ? "Nueva contraseña (opcional)" : "Contraseña"} type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} hint="Mínimo 6 caracteres." />
              </div>
            </DemoLock>
            {form.id && (
              <DemoLock>
                <label className="flex cursor-pointer items-center gap-2 self-end pb-2 text-sm text-text">
                  <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Activo
                </label>
              </DemoLock>
            )}
            {err && <div className="sm:col-span-2"><Notice kind="danger">{err}</Notice></div>}
            <div className="flex justify-end gap-2 sm:col-span-2"><Button variant="ghost" onClick={() => setForm(null)}>Cancelar</Button><Button variant="primary" onClick={save}>Guardar</Button></div>
          </div>
        )}
      </Modal>
      <Modal open={!!del} onClose={() => setDel(null)} title={`¿Eliminar @${del?.username}?`}>
        <p className="text-sm text-secondary">Esta acción no se puede deshacer.</p>
        <div className="mt-4 flex justify-end gap-2"><Button variant="ghost" onClick={() => setDel(null)}>Cancelar</Button><Button variant="danger" icon={Trash2} onClick={remove}>Eliminar</Button></div>
      </Modal>
    </div>
  );
}
