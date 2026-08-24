import { createHashHistory, createRouter } from "@tanstack/react-router"
import { routeTree } from "./routeTree.gen"
import { queryClient } from "@/lib/query-client"

const hashHistory = createHashHistory()

export const router = createRouter({
  routeTree,
  history: hashHistory,
  context: {
    queryClient,
  },
  defaultPreload: "intent",
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
