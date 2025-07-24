import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Hub, Auth } from 'aws-amplify';

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signIn' || payload.event === 'cognitoHostedUI') {
        router.replace('/');
      }
      if (payload.event === 'signIn_failure' || payload.event === 'cognitoHostedUI_failure') {
        console.error('OAuth sign-in failed:', payload.data);
        router.replace('/login');
      }
    });

    // Also check if already authenticated (in case Hub event already fired)
    Auth.currentAuthenticatedUser()
      .then(() => router.replace('/'))
      .catch(() => {}); // not yet authenticated, wait for Hub

    return unsubscribe;
  }, [router]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      Completing sign-in...
    </div>
  );
}
