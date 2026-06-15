import { createBrowserRouter } from "react-router";
import App from './App.tsx'
import BenchmarksPage from "./historyPage.tsx";
import ForYouDesktop from "./forYouPage.tsx";

export default createBrowserRouter([
  {
    path: "/",
    element: <App/>,
  },
  {
    path: "/history",
    element: <BenchmarksPage/>,
  },
  {
    path: "/foryou",
    element: <ForYouDesktop/>
  }
]);
