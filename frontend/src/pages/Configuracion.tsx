import { Bot, DatabaseBackup, Download, RefreshCcw, Save, Settings as SettingsIcon, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { DemoLock } from "../components/DemoLock";
import { Field } from "../components/fields";
import { Button, Card, Modal, Notice, PageHeader, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import type { Settings } from "../lib/types";

export default function Configuracion() {
  const toast = useToast();
  const { data, reload } = useApi<Settings>("/api/settings");
  const ai = useApi<{ enabled: boolean; model: string | null }>("/api/ai/status");
  const [form, setForm] = useState<Settings | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  async function save() {
    try {
      await api.put("/api/settings", form);
      toast("Parámetros guardados.");
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  async function reseed() {
    setBusy(true);
    try {
      const r = await api.post<{ orders: number }>("/api/admin/reseed");
      toast(`Datos regenerados: ${r.orders} órdenes ficticias.`);
      setConfirm(false);
      setTimeout(() => window.location.reload(), 600);
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setBusy(false);
    }
  }

  async function restore(f: File) {
    const fd = new FormData();
    fd.append("file", f);
    try {
      await api.upload("/api/admin/restore", fd);
      toast("Respaldo restaurado.");
      setTimeout(() => window.location.reload(), 600);
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  return (
    <div>
      <PageHeader icon={SettingsIcon} title="Configuración" crumbs={[{ label: "Administración" }, { label: "Configuración" }]} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Parámetros del taller">
          {form && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Tarifa por hora estándar (MXN)" type="number" min={0} step={10} value={form.labor_rate} onChange={(e) => setForm({ ...form, labor_rate: Number(e.target.value) })} />
              <Field label="Margen (%)" type="number" min={0} value={Math.round(form.margin_pct * 100)} onChange={(e) => setForm({ ...form, margin_pct: Number(e.target.value) / 100 })} />
              <Field label="Meta de eficiencia (%)" type="number" min={50} max={150} value={Math.round(form.efficiency_goal * 100)} onChange={(e) => setForm({ ...form, efficiency_goal: Number(e.target.value) / 100 })} hint="Al alcanzarla se celebra con confeti." />
              <Field label="Nivel de servicio del inventario (%)" type="number" min={50} max={99.9} step={0.5} value={Math.round(form.service_level * 1000) / 10} onChange={(e) => setForm({ ...form, service_level: Number(e.target.value) / 100 })} hint="Define z en el stock de seguridad." />
              <div className="sm:col-span-2"><Button variant="primary" icon={Save} onClick={save}>Guardar</Button></div>
            </div>
          )}
        </Card>
        <Card title={<span className="inline-flex items-center gap-2"><Bot size={16} className="text-accent" aria-hidden />Inteligencia artificial</span>}>
          {ai.data?.enabled
            ? <Notice kind="success">IA activa con Groq · modelo <code>{ai.data.model}</code>. Solo interpreta y redacta; nunca calcula precios ni métricas.</Notice>
            : <Notice kind="info">IA desactivada. Agrega <code>GROQ_API_KEY</code> en <code>.env</code> (local) o en las variables de entorno de Render.</Notice>}
        </Card>
        <Card title={<span className="inline-flex items-center gap-2"><DatabaseBackup size={16} className="text-accent" aria-hidden />Respaldo de la base</span>}>
          <p className="mb-3 text-sm text-secondary">En Render (plan gratis) el disco es temporal: descarga un respaldo y restáuralo cuando quieras. También puedes apuntar <code>TALLER_DB_PATH</code> a un disco persistente.</p>
          <div className="flex flex-wrap gap-2">
            <Button icon={Download} onClick={() => api.download("/api/admin/backup", `taller_${new Date().toISOString().slice(0, 10)}.db`).catch((e) => toast(e.message, "danger"))}>Descargar respaldo</Button>
            <DemoLock><Button icon={Upload} onClick={() => file.current?.click()}>Restaurar respaldo</Button></DemoLock>
            <input ref={file} type="file" accept=".db,.sqlite" className="hidden" onChange={(e) => e.target.files?.[0] && restore(e.target.files[0])} />
          </div>
        </Card>
        <Card title="Datos de demostración">
          <p className="mb-3 text-sm text-secondary">Borra todo y genera de nuevo ~6 meses de datos ficticios (semilla 42), con los usuarios demo.</p>
          <DemoLock><Button variant="danger" icon={RefreshCcw} onClick={() => setConfirm(true)}>Regenerar datos</Button></DemoLock>
        </Card>
      </div>
      <Modal open={confirm} onClose={() => setConfirm(false)} title="¿Regenerar todos los datos?">
        <Notice kind="warning">Se borrarán órdenes, usuarios creados y cambios del catálogo. Las contraseñas demo vuelven a «demo123».</Notice>
        <div className="mt-4 flex justify-end gap-2"><Button variant="ghost" onClick={() => setConfirm(false)}>Cancelar</Button><Button variant="danger" loading={busy} icon={RefreshCcw} onClick={reseed}>Regenerar</Button></div>
      </Modal>
    </div>
  );
}
