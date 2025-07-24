import { useEffect } from 'react';
import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import AuthGuard from '../components/AuthGuard';
import { configureAmplify } from '../utils/auth';
import '../styles/globals.css';
import '../styles/DarkTheme.css';

const awsConfig = {
  region: 'us-east-1',
  userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || 'your-user-pool-id',
  userPoolWebClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || 'your-client-id',
  federatedSsoEnabled: process.env.NEXT_PUBLIC_FEDERATED_SSO_ENABLED === 'true',
  cognitoDomain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN || '',
};

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();

  useEffect(() => {
    configureAmplify(awsConfig);
  }, []);

  // Skip auth check for login, signup, and OAuth callback pages
  const isAuthPage = router.pathname === '/login' || router.pathname === '/signup' || router.pathname === '/auth/callback';

  return (
    <>
      {isAuthPage ? (
        <Component {...pageProps} />
      ) : (
        <AuthGuard>
          <Component {...pageProps} />
        </AuthGuard>
      )}
    </>
  );
}