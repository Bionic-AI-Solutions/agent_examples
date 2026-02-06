import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/unauthorized'])

// Allowed email domains (add your domains here)
const ALLOWED_DOMAINS = ['bionicaisolutions.com', 'zippio.ai', 'gmail.com'] // Update this list

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    const { userId, sessionClaims } = await auth()

    // Require authentication
    if (!userId) {
      await auth.protect()
      return
    }

    // Check if user's email domain is allowed
    const email = sessionClaims?.email as string | undefined

    if (email) {
      const emailDomain = email.split('@')[1]
      if (!ALLOWED_DOMAINS.includes(emailDomain)) {
        // Redirect to unauthorized page
        return Response.redirect(new URL('/unauthorized', request.url))
      }
    }
  }
})

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
