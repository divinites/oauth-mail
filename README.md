# oauth-mail

I developed the oauth-mail plug-in because I sometimes want to send directly what I wrote in sublime text, and I do not want to enter my password every time or store my plain-text email account name and password somewhere. That's why I choose to support oauthv2. with oauth method, the password will not be leaked to the third party, so it is basically safer. Nevertheless, there are still potential risks that other malicious plug-ins (if any) will get the cached "access_token" and obtain the access privileges that you grant to sublime text editor. All in all, Use this plug-in at your own risk, I will not take any responsibility for any loss.  

## Set-up steps:

Currently, oauth-mail supports Microsoft outlook.com (including hotmail, livemail, etc.) and gmail. 

Before using Oauth Mail, you need do some simple steps to set up it.

The setting template is

Preference -> Package Settings -> Oauth Mail -> Mail settings - Default

 you should copy it and paste to

Preference -> Package Settings -> Oauth Mail -> Mail settings - User

to configure your own mail settings.

### Gmail Settings:

Gmail setup is quite simple, 

1. Go to [Google dev centre](https://console.developers.google.com/project), create a project. Here is a nice tutorial if you are not familiar with that [How to obtain Google Client ID and Secret](https://www.youtube.com/watch?v=o425vQXpigw).

Now, you have a client ID and Client Secret, copy and paste them into the Mail settings - User and it simply works.

Google also provide a downloadable json-format configuration file (including client_id, client_secret, auth_uri and etc.). If you prefer to use this, you can download it and copy the full path, create an entry "client_secret_file" just before "client_id", and paste the path of your downloaded configuration file. It should also do the job.


####  Microsoft Mail settings:

1. go to [microsoft dev centre](https://account.live.com/developers/applications/index), create an application.

2. In the API settings, you will find your client_id and client_secret, fill in the scope with ** wl.imap**, choose no for mobile client.

3. Microsoft's policy about the redirect URI is quite tricky, it must be in the form http://www.xxx.com:[port], so in the current version, I hard code http://www.mylocalhost.com:10111 as the default redirect url, please fill in the API settings as well. in the future version,  I will add an option entry so that users can choose there preferred names in *mail.sublime-settings*.

4. modify your host file: for osx users, it is /etc/host, add a new line *127.0.0.1  www.mylocalhost.com* at the end.


##  Functions:

- Write Mail: do exactly as the command name describes, this command will open a new view
- Send Mail:  do exactly as the command name, describes, this command will send the mail you write
- Send As Mail: this command will add email header on top of all the content in current view
- Show Mail List: this command will show the default email list, you can set it in user setting files.
- Show Mail: it would be better to use it after show mail list, since this command with show an input panel, you can enter the mail ID (listed by show_mail_list command) and a new view will open and show your mail content.

That's it. In the first time you use this plug-in, it will redirect your an authorization page, where you can click "yes" for authorization, after you see the page "the authentication flow has completed", you can close that page and let the program take in charge everything. In the next time and what soever, you can instantly send emails without any noticeable interaction with email server, since the program will automatically deal with everything and refresh the access_token when necessary. 

## Future Development:

1. This project is still in a very early stage, now it supports sending and receiving mails via Outlook mails and Gmails. You are welcome to send me request about more email server support, or, send me a pull request. 
2. Next step: 
   - Adding signature support
   - ~~Adding IMAP support, so users will be able to receive recent emails~~
   - Adding reply and forwarding command
   - Using tmLanguage to define different colors when displaying email list

I have no intention to make it a full functional email agent with complicated rules, since we already have so many excellent programs. I will keep it light-weight, only necessary functions will be added.

## Change Logs:

- v. 0.1.1 The first commitment
- v. 0.2.0 re-write using oauthmail API
- v. 0.3.0 IMAP fully worked
- v. 0.3.1 minor changes
- v. 0.3.5 correct some minor errors
- v. 0.4.0 add YAML support
- v. 0.5.0 accepted by package control channel


## Thanks:

Special thanks to [klorenz's project sublime-email](https://bitbucket.org/klorenz/sublimeemail/) and many stack-overflow answers.
