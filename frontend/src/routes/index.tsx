import { lazy, Suspense } from "react";
import { createBrowserRouter, type RouteObject } from "react-router-dom";
import ErrorBoundary from "../components/ErrorBoundary";

const Home = lazy(() => import("../pages/Home"));
const History = lazy(() => import("../pages/History"));
const Detail = lazy(() => import("../pages/Detail"));

function PageFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
    </div>
  );
}

function withBoundary(element: React.ReactNode) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageFallback />}>{element}</Suspense>
    </ErrorBoundary>
  );
}

export const routes: RouteObject[] = [
  {
    path: "/",
    element: withBoundary(<Home />),
  },
  {
    path: "/history",
    element: withBoundary(<History />),
  },
  {
    path: "/detail/:token",
    element: withBoundary(<Detail />),
  },
];

export const router = createBrowserRouter(routes);