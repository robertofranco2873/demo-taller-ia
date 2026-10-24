import { Lock, MapPinOff } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui";

function Message({ icon: Icon, title, text }: { icon: typeof Lock; title: string; text: string }) {
  return (
    <Card className="mx-auto mt-10 max-w-md text-center">
      <Icon className="mx-auto mb-3 text-accent" size={36} aria-hidden />
      <h1 className="text-lg font-bold text-text">{title}</h1>
      <p className="mt-1 text-sm text-secondary">{text}</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-link hover:underline">Ir a mi inicio</Link>
    </Card>
  );
}

export function Forbidden() {
  return <Message icon={Lock} title="Sin permiso" text="Tu rol no tiene acceso a este módulo. El servidor también lo bloquea." />;
}

export function NotFound() {
  return <Message icon={MapPinOff} title="Página no encontrada" text="La ruta que buscas no existe." />;
}
