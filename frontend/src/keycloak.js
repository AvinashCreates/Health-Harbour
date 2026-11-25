import Keycloak from 'keycloak-js'

const enabled = import.meta.env.VITE_AUTH_PROVIDER === 'keycloak'
const keycloak = enabled
  ? new Keycloak({
      url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
      realm: import.meta.env.VITE_KEYCLOAK_REALM || 'healthharbor',
      clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'healthcare-exchange-web',
    })
  : null

export { enabled as keycloakEnabled, keycloak }
