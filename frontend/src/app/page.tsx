export default function Home() {
  return (
    <main className="grid min-h-screen place-items-center p-8">
      <div className="max-w-md space-y-3 text-center">
        <h1 className="text-3xl font-bold">3D Printing PIM</h1>
        <p className="text-sm text-muted-foreground">
          Scaffold ready. Mount feature routes dưới{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            src/app/(admin)
          </code>{" "}
          và{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            src/app/(pos)
          </code>
          .
        </p>
      </div>
    </main>
  );
}
