import { lazy, Suspense } from "react";
import { createBrowserRouter, type RouteObject } from "react-router-dom";
import ErrorBoundary from "../components/ErrorBoundary";

const Welcome = lazy(() => import("../pages/Welcome"));
const Home = lazy(() => import("../pages/Home"));
const History = lazy(() => import("../pages/History"));
const Detail = lazy(() => import("../pages/Detail"));
const Login = lazy(() => import("../pages/Login"));
const Profile = lazy(() => import("../pages/Profile"));
const ArticleEditor = lazy(() => import("../pages/ArticleEditor"));
const Community = lazy(() => import("../pages/Community"));
const PostDetail = lazy(() => import("../pages/PostDetail"));
const PostPublish = lazy(() => import("../pages/PostPublish"));
const FoodPlaza = lazy(() => import("../pages/FoodPlaza"));
const TrainingReview = lazy(() => import("../pages/TrainingReview"));

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
    element: withBoundary(<Welcome />),
  },
  {
    path: "/home",
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
  {
    path: "/login",
    element: withBoundary(<Login />),
  },
  {
    path: "/profile",
    element: withBoundary(<Profile />),
  },
  {
    path: "/article/edit",
    element: withBoundary(<ArticleEditor />),
  },
  {
    path: "/community",
    element: withBoundary(<Community />),
  },
  {
    path: "/community/post",
    element: withBoundary(<PostPublish />),
  },
  {
    path: "/post/:id",
    element: withBoundary(<PostDetail />),
  },
  {
    path: "/food",
    element: withBoundary(<FoodPlaza />),
  },
  {
    path: "/training-review",
    element: withBoundary(<TrainingReview />),
  },
];

export const router = createBrowserRouter(routes);
