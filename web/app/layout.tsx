import Link from "next/link";
import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Committee of Fifteen — NYC 1900",
  description: "Map and search NYPL vice investigation affidavits (~1900 NYC)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="siteHeader">
          <Link href="/" className="brand">
            Committee of Fifteen
          </Link>
          <nav>
            <Link href="/map">Map</Link>
            <Link href="/search">Search</Link>
            <a
              href="https://github.com/tedrubin80/commitieoffifteen"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="siteFooter">
          Source:{" "}
          <a href="https://digitalcollections.nypl.org/collections/216eff30-6f84-0133-9b03-00505686d14e">
            NYPL Digital Collections
          </a>
          · Rights undetermined on many items — research use; link to NYPL for scans.
        </footer>
      </body>
    </html>
  );
}
