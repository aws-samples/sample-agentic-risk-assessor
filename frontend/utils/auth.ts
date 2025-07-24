import { Amplify, Auth } from 'aws-amplify';

// Initialize Amplify with Cognito configuration
// These values would come from your Terraform outputs
export const configureAmplify = (config: {
  userPoolId: string;
  userPoolWebClientId: string;
  region: string;
  cognitoDomain?: string;
  federatedSsoEnabled?: boolean;
}) => {
  const amplifyConfig: any = {
    Auth: {
      region: config.region,
      userPoolId: config.userPoolId,
      userPoolWebClientId: config.userPoolWebClientId,
      mandatorySignIn: true,
    }
  };

  if (config.federatedSsoEnabled && config.cognitoDomain) {
    amplifyConfig.Auth.oauth = {
      domain: config.cognitoDomain,
      scope: ['phone', 'email', 'openid', 'profile'],
      redirectSignIn: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : '',
      redirectSignOut: typeof window !== 'undefined' ? `${window.location.origin}/` : '',
      responseType: 'code',
    };
  }

  Amplify.configure(amplifyConfig);
};

// Sign in with email and password
export const signIn = async (email: string, password: string) => {
  try {
    const user = await Auth.signIn(email, password);
    return { user, error: null };
  } catch (error: any) {
    return { user: null, error: { message: error.message || 'Failed to sign in' } };
  }
};

// Sign in with Federated SSO (OIDC provider)
export const signInWithFederatedSSO = () => {
  Auth.federatedSignIn({ customProvider: process.env.NEXT_PUBLIC_FEDERATED_SSO_PROVIDER || 'CorporateSSO' } as any);
};

// Sign up with email and password
export const signUp = async (email: string, password: string) => {
  try {
    const { user } = await Auth.signUp({
      username: email,
      password,
      attributes: {
        email,
      },
    });
    return { user, error: null };
  } catch (error: any) {
    return { user: null, error: { message: error.message || 'Failed to sign up' } };
  }
};

// Sign out
export const signOut = async () => {
  try {
    await Auth.signOut();
    return { error: null };
  } catch (error: any) {
    return { error: { message: error.message || 'Failed to sign out' } };
  }
};

// Get current authenticated user
export const getCurrentUser = async () => {
  try {
    const user = await Auth.currentAuthenticatedUser();
    return { user, error: null };
  } catch (error: any) {
    return { user: null, error: { message: error.message || 'No authenticated user' } };
  }
};

// Check if user is authenticated
export const isAuthenticated = async () => {
  try {
    await Auth.currentAuthenticatedUser();
    return true;
  } catch {
    return false;
  }
};

// Get JWT token
export const getJwtToken = async () => {
  try {
    const session = await Auth.currentSession();
    return session.getIdToken().getJwtToken();
  } catch (error) {
    console.error('Failed to get JWT token:', error);
    return null;
  }
};