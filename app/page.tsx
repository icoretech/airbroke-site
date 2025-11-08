// app/page.tsx

import Image from "next/image";
import Link from "next/link";
import { FaGithub } from "react-icons/fa";
import PageBackground from "@/components/PageBackground";
import { CodeBlock } from "@/components/CodeBlock";
import FooterCredits from "@/components/FooterCredits";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const jsSnippet = `import { Notifier } from '@airbrake/browser'

const airbrake = new Notifier({
  projectId: 1,
  projectKey: 'YOUR_API_KEY',
  environment: 'production',
  host: 'https://your-airbroke-host',
  remoteConfig: false,
  performanceStats: false,
  queryStats: false,
  queueStats: false,
})

airbrake.notify(new Error('Hello from Airbroke'))`;

  return (
    <div className="h-full bg-background">
      {/* Hero */}
      <div className="relative isolate overflow-hidden">
        <PageBackground>
        <div className="mx-auto max-w-7xl px-6 pb-20 pt-16 sm:pb-28 lg:flex lg:items-center lg:gap-12 lg:px-8 lg:py-28">
          {/* Left: brand + copy + CTAs */}
          <div className="mx-auto max-w-2xl shrink-0 lg:mx-0 lg:max-w-xl">
            <div className="flex items-center">
              <Image
                src="/logo.svg"
                alt="Airbroke"
                width={463}
                height={338}
                priority
                className="h-10 w-auto md:h-12"
              />
            </div>
            <h1 className="mt-6 text-4xl font-bold tracking-tight text-foreground sm:text-6xl">
              Error tracking that fits your stack
            </h1>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              <strong>Airbroke</strong> ingests errors via an
              Airbrake-compatible API, stores them in Postgres, and gives you a
              modern, low-overhead UI with AI assistance, HTTP replay, and
              occurrence charts.
            </p>
            <div className="mt-8 flex items-center gap-3">
              <Button asChild>
                <a
                  href="https://github.com/icoretech/airbroke/blob/main/README.md#deployment-options"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Setup Guide
                </a>
              </Button>
              <Button asChild variant="outline">
                <a
                  href="https://github.com/icoretech/airbroke"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <FaGithub className="mr-2" /> GitHub
                </a>
              </Button>
              <a
                href="https://github.com/icoretech/airbroke/releases"
                className="text-sm font-semibold leading-6 text-foreground"
                target="_blank"
                rel="noopener noreferrer"
              >
                Releases →
              </a>
            </div>
          </div>

          {/* Right: single quickstart code */}
          <div className="mx-auto mt-12 w-full max-w-2xl lg:mt-0 lg:flex-1">
            <div className="rounded-xl border border-white/10 bg-card/70 p-4 shadow-sm ring-1 ring-white/5 backdrop-blur">
              <CodeBlock
                language="javascript"
                filename="quickstart.js"
                code={jsSnippet}
              />
            </div>
          </div>
        </div>
        </PageBackground>
      </div>

      {/* FAQ (minimal) */}
      <section className="border-t border-white/5 bg-background py-16">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">
            FAQ
          </h2>
          <div className="mt-6 space-y-4">
            <details className="group rounded-lg border border-white/10 bg-card p-4 open:bg-airbroke-700/20">
              <summary className="cursor-pointer list-none text-lg font-medium text-foreground">
                Is Airbroke compatible with Airbrake clients?
              </summary>
              <p className="mt-2 text-muted-foreground">
                Yes. Airbroke implements an Airbrake-compatible API. Point your 
                Airbrake client to your Airbroke host, and it will work.
              </p>
            </details>
            <details className="group rounded-lg border border-white/10 bg-card p-4 open:bg-airbroke-700/20">
              <summary className="cursor-pointer list-none text-lg font-medium text-foreground">
                What databases are supported?
              </summary>
              <p className="mt-2 text-muted-foreground">
                Postgres. Airbroke purposely keeps infra simple and affordable.
              </p>
            </details>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-background py-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 text-sm text-muted-foreground lg:px-8">
          <div>
            <FooterCredits />
          </div>
          <div>
            <a href="https://github.com/icoretech/airbroke" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 hover:text-foreground">
              <FaGithub /> GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
