import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nexo · Tus solicitudes, en un solo lugar",
  description:
    "Demo de gestión de peticiones, quejas y reclamos con Firebase y Google ADK.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
