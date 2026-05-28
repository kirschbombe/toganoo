import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CollectionView from '../views/CollectionView.vue'
import ViewerView from '../views/ViewerView.vue'
import AdminView from '../views/AdminView.vue'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/',            component: HomeView },
  { path: '/collection',  component: CollectionView },
  { path: '/viewer/:slug', component: ViewerView },
  {
    path: '/admin',
    component: AdminView,
    beforeEnter: () => {
      const auth = useAuthStore()
      if (!auth.user?.is_admin) return '/'
    },
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
