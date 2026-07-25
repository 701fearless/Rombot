import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { FeedPage } from '@/pages/FeedPage'
import { SceneEditorPage } from '@/pages/SceneEditorPage'
import {
  CompletePage,
  DashboardPage,
  DiscoverPage,
  HomePage,
  MePage,
  ProductPage,
  RecognizePage,
  RecommendPage,
  ScenePage,
  SuggestPage,
} from '@/pages/WorkspacePages'

function LegacyRedirect() {
  const { pathname, search } = useLocation()
  const routes: Record<string, string> = {
    '/pages/discover/index': '/', '/pages/myhome/index': '/home', '/pages/direction/index': '/discover',
    '/pages/remodel/index': '/me', '/pages/flow/recognize/index': '/recognize',
    '/pages/flow/place/index': '/space', '/pages/flow/suggest/index': '/suggest',
    '/pages/flow/recommend/index': '/recommend', '/pages/flow/complete/index': '/complete',
  }
  return <Navigate replace to={`${routes[pathname] ?? '/'}${search}`} />
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<FeedPage />} />
        <Route path='home' element={<HomePage />} />
        <Route path='discover' element={<DiscoverPage />} />
        <Route path='me' element={<MePage />} />
      </Route>
      <Route path='product/:id' element={<ProductPage />} />
      <Route path='scene/:id' element={<ScenePage />} />
      <Route path='recognize' element={<RecognizePage />} />
      <Route path='space' element={<SceneEditorPage />} />
      <Route path='suggest' element={<SuggestPage />} />
      <Route path='recommend' element={<RecommendPage />} />
      <Route path='complete' element={<CompletePage />} />
      <Route path='dashboard' element={<DashboardPage />} />
      <Route path='feed' element={<Navigate replace to='/' />} />
      <Route path='pages/*' element={<LegacyRedirect />} />
      <Route path='*' element={<Navigate replace to='/' />} />
    </Routes>
  )
}
