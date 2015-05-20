# oauth-mail

I developed the oauth-mail plug-in because I sometimes want to send directly what I wrote in sublime text, and I do not want to enter my password every time or store my plain-text email account name and password somewhere. That's why I choose to support oauthv2. with oauth method, the password will not be leaked to the third party, so it is basically safer. Nevertheless, there are still potential risks that other malicious plug-ins (if any) will get the cached "access_token" and obtain the access privileges that you grant to sublime text editor. All in all, Use this plug-in at your own risk, I will not take any responsibility for any loss.  

## Set-up steps:

Currently, oauth-mail supports Microsoft outlook.com (including hotmail, livemail, etc.) and gmail. 

### Gmail Settings:

Gmail setup is quite simple, 

1. Go to [Google dev centre](https://console.developers.google.com/project), create a project. Here is a nice tutorial if you are not familiar with that [How to obtain Google Client ID and Secret](https://www.youtube.com/watch?v=o425vQXpigw).

2. Download the json file to oath-mail directory, named it with whatever you want.

3. Now you have two options:
   - Open "mail.sublime-settings", put your json file's name behind the entry "client_secret_file" and that's it.
   - Open the downloaded json file, create two entries "client_id" and "client_secret" and fill in the correct value according to your downloaded file.

####  Microsoft Mail settings:

1. go to [microsoft dev centre](https://account.live.com/developers/applications/index), create an application.

2. In the API settings, you will find your client_id and client_secret, fill in the scope with ** wl.imap**, choose no for mobile client.

3. Microsoft's policy about the redirect URI is quite tricky, it must be in the form http://www.xxx.com:[port], so in the current version, I hard code http://www.mylocalhost.com:10111 as the default redirect url, please fill in the API settings as well. in the future version,  I will add an option entry so that users can choose there preferred names in *mail.sublime-settings*.

4. modify your host file: for osx users, it is /etc/host, add a new line *127.0.0.1  www.mylocalhost.com* at the end.



That's it. In the first time you use the send mail, it will redirect your an authorization page, where you can click "yes" for authorization, after you see the page "the authentication flow has completed", you can close that page and let the program take in charge everything. In the next time and what soever, you can instantly send emails without any noticeable interaction with email server, since the program will automatically deal with everything and refresh the access_token when necessary. 

## Future Development:

1. This project is still in its early stage, now it suppport sending and receiving mails via Outlook mails and Gmails. 
2. Next step: 
   - Adding signature support
   - ~~Adding IMAP support, so users will be able to receive recent emails~~
   - Adding reply and forwarding command

I have no intention to make it a full functional email agent with complicated rules, since we already have so many execellent programs. I will keep it light-weight, only necessary functions will be added.

## Change Logs:

- v. 0.1.1 The first commitment
- v. 0.2.0 re-write using oauthmail API
- v. 0.3.0 IMAP fully worked
- v. 0.3.1 minor changes
- v. 0.3.5 correct some minor errors


## Thanks:

Special thanks to [klorenz's project sublime-email](https://bitbucket.org/klorenz/sublimeemail/) and many stack-overflow answers.
