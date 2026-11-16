import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Foco Social — análisis de conversación",
  description: "Explorá mensajes, descubrí temas y entendé qué conversaciones están marcando el pulso.",
  applicationName: "Foco Social",
};

export const viewport: Viewport = {
  themeColor: "#f3f4ee",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es-AR" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
