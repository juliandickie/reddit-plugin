# Reddit Data API access request - draft answers

Drafted 2026-09-11 from the live form at
https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164
and the Responsible Builder Policy as published that day. Julian files it; the form
is a Zendesk ticket and cannot be submitted from a script.

## What the form actually is

One ticket form, "Data Access Request", with a role dropdown that reveals one of three
question sets. Every field is optional in the HTML, so an answer left blank is a
choice the reviewer sees.

| Track | Reached by | Questions revealed |
|---|---|---|
| Commercial (Reddit calls it enterprise) | the "contact form" link under "Commercial Use" | company name, corporate email, full name, phone, current use of Reddit data, website, company description with industries and locations, company size, purpose of the product, what you deliver to users with Reddit data, what you distribute and to whom, data budget |
| Developer (bot or app) | "sign up here" under non-commercial Data API | benefit for Redditors, detailed description of what the bot or app will do ON Reddit, what is missing from Devvit, link to source code, subreddits it will run in, operating username, existing bot usernames |
| Researcher | the Reddit for Researchers link | institution, country, research purpose, timeline, and a checkbox affirming non-commercial academic use |

## The constraint that decides the track

Reddit's own definitions, quoted from the help article and the policy on 2026-09-11:

- "We consider commercial purposes to include any use of our services by a business
  or on behalf of a business or as part of a monetized product or service."
- "Be transparent: You must not misrepresent or mask how or why you are accessing
  Reddit data."
- Enforcement: "Revoking your access tokens. Suspending your app or account.
  Suspending associated accounts, bots, domains, or subreddits."

A read-only research CLI used by iDD and by Pro Marketing for its clients is
commercial under the first line, whoever fills the form. Filing it on the developer
track while describing it as a hobby or personal tool would breach the second line,
and the third line is what that risks: Julian's own Reddit account and any iDD or Pro
Marketing accounts associated with it.

The developer track is also shaped for something else. Its questions assume an app
that acts on Reddit for Redditors' benefit and asks why Devvit cannot host it. A tool
that only reads threads into a local research file has no honest answer to "what
benefit will the app have for Redditors", and a reviewer will notice a blank.

**Recommendation.** File the commercial track, honestly and minimally. It is slower
and may come back with a contract or a fee, and it may be declined. That is a better
outcome than an approval that evaporates with the accounts attached to it.

**Julian's decision, 2026-09-11: file the developer track with the honest answers
below.** He read the finding above and chose the faster track knowing Reddit may reject
it or redirect to commercial. The answers are written so they are true on either form.
Nothing in them claims the use is personal or non-commercial, and nothing hides that a
business uses it; that is the line that keeps the account safe whichever way Reddit
rules.

**Amended 2026-09-27, at Julian's request - agency research added.** The 11 September
draft described dentistry research for iDD only. Only one ticket is allowed per use
case, and the policy requires transparency about why data is accessed, so the ticket
now covers every intended use:
- tool and service research for Pro Marketing's own operations (the first real use,
  the DMARC monitoring decision of 2026-09-26)
- customer-language research in a client's category
- the original iDD dental education research

The "current use" answer is also corrected. The draft said no Reddit data had been
collected, which stopped being true on 2026-09-26 when an Apify scrape (trudax/reddit-scraper-lite)
ran for the DMARC research. Filing the old line would misrepresent how the data was
accessed, which is the exact breach the policy names.

The wider scope also strengthens the finding above: client-facing agency work is
plainly commercial, and the developer track fits it less well than it fitted the
original draft. The track choice stays Julian's. The answers below are still written
to be true on either form.

## Draft answers, written to be true on either track

**Subject of inquiry**
Read-only Data API access for a small internal research CLI

**Your Reddit username**
(Julian's handle, without u/)

**Company name**
Pro Marketing Pty Ltd

**Corporate email address**
julian@promarketing.co

**Company website URL**
https://promarketing.co

**Company description, including industries served and locations**
A small Australian web and marketing agency in Brisbane and Bundaberg, Queensland. It
builds websites, runs search, advertising and email marketing, and monitors the
technical health of client websites and email domains. Clients are local and
professional-services businesses in Australia, and an online dental education
company, the Institute of Digital Dentistry, serving dentists in Australia, New
Zealand, Canada and the US.

**Company size**
Under 20 people.

**Your current use of Reddit data**
In September 2026, before filing this request, we used a third-party scraping service
(Apify) for one research pass. It read public posts and comments about email
authentication tools, in subreddits such as r/msp and r/sysadmin, to inform an internal
decision about which tool to use. Before that, every attempt to read Reddit went
through the public site or a third-party connector, and those are now blocked. We are
asking for API access so that future research goes through the sanctioned route
instead.

**What is the purpose of your product or service?**
An internal command-line tool that reads public Reddit threads and comments for three
kinds of research. All of it is read-only and small in volume.
1. Choosing tools and services. We read practitioner discussions (IT administration,
   email deliverability, web hosting, self-hosting, marketing operations) when we choose
   the software we run or recommend to clients. An example is how agencies monitor
   email authentication (DMARC) across many client domains.
2. Customer language for a client's category. Before we write for a client, we read
   what customers in that category ask and complain about, for example first-home
   buyers, landlords or people seeking acupuncture. That way the website and
   educational material answer real questions in plain words.
3. Dental education. We read what dentists say about learning digital dentistry, to
   shape course descriptions and educational material for the Institute of Digital
   Dentistry.
It does not monitor brands, track individuals, profile users, or collect personal
data. Nothing is built for resale, nothing is republished, and no Reddit content
appears in any product.

**What will you deliver to your users/customers with Reddit data?**
Nothing containing Reddit data. The output is internal research notes that summarise
themes, used by our own staff. Work delivered to clients (web pages, advice, reports)
is our own writing informed by those themes. It contains no Reddit posts, quotes,
usernames or derived datasets. No Reddit content or derived data is distributed,
licensed, displayed or sold, and nothing is used to train any model.

**Please describe what you are planning to distribute, where it will be distributed
and expected audience.**
Nothing is distributed. Reads stay on one machine as local files with an audit of what
was read and why, retained only while the research question is open.

**Provide a detailed description of what the app will be doing on the Reddit platform**
Read-only. Searches public subreddits chosen per research question (for example
r/msp, r/sysadmin, r/emailmarketing and r/selfhosted for tool research, category
communities such as r/AusFinance or r/AusProperty for a client's customers, and
r/Dentistry and r/dentaltechnology for dental education). Fetches individual public
threads with their comment trees and saves them locally. It never posts, comments, votes, messages, or acts as an account.
Authentication is OAuth with read-only scopes. Volume is small: a research pass is
tens of threads, well under 100 requests per minute and typically a few hundred
requests per day at most.

**Provide a link to source code or platform that will access the API**
https://github.com/juliandickie/reddit-plugin (public from 2026-09-11 if Julian makes
the repos public as planned; otherwise say "private repository, source available on
request")

**What is missing from Devvit that prevents building on that platform?**
Devvit hosts apps that run inside Reddit for Redditors. This is not that. It is a
local research reader that pulls a handful of public threads into a file on one
machine, so there is no in-Reddit surface for it and no audience of Redditors.

**What subreddits do you intend to use the bot/app in?**
It reads only, and posts in none. Subreddits are chosen per research question: IT
administration, email and marketing-operations communities for tool research;
consumer and category communities for a client's customers (property, finance,
health, trades); and dentistry and dental-technology communities for education.

**If applicable, what username will you be operating this app under?**
Julian's own account, read-only, no posting.

**What benefit/purpose will the app have for Redditors?**
None directly, and this answer should not pretend otherwise. It reads public posts so
that the websites, advice and educational material we write answer the questions
people actually ask, in the words they actually use.

**What is your data budget?**
None allocated. If access carries a fee, tell us the number and we will decide whether
the research question justifies it.

## Do not

- Do not describe the tool as personal, hobby, or non-commercial. It is used by a
  business.
- Do not add brand monitoring, reputation tracking or social listening for clients to
  the ticket. The tool is not built or used for any of them. If that ever changes, it
  is a new use case that needs Reddit's agreement first, not a quiet extension of
  this one.
- Do not file with the "current use" answer out of date. If more research has run
  through Apify or anything else since 2026-09-27, say so.
- Do not file more than one ticket. The policy treats duplicate requests for the same
  use case as a breach.
- Do not tick the researcher checkbox. That track is for academic institutions.

## After filing

Record the ticket number and date in `CLAUDE.md` under the status line, and note the
track chosen. When credentials arrive, follow README "Set up credentials"; the
redirect URI is `http://localhost:8250/callback`.
