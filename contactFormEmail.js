var AWS = require('aws-sdk')
var ses = new AWS.SES()

var RECEIVERS = ['info@rsindustries.io'];
var SENDER = 'info@rsindustries.io'; // make sure that the sender email is properly set up in your Amazon SES

exports.handler = (event, context, callback) => {
    console.log('Received event:', event);
    sendEmail(event, function (err, data) {
        var response = {
            "isBase64Encoded": false,
            "headers": { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': 'https://rsindustries.io' },
            "statusCode": 200,
            "body": "{\"result\": \"Success.\"}"
        };
        callback(err, response);
    });
};

function sendEmail (event, done) {
    var data = JSON.parse(event.body);

    var params = {
        Destination: {
            ToAddresses: RECEIVERS
        },
        Message: {
            Body: {
                Text: {
                    Data: 'Name: ' + data.firstname + ' ' + data.lastname + '\nEmail: ' + data.email + '\nMessage: ' + data.message,
                    Charset: 'UTF-8'
                }
            },
            Subject: {
                Data: 'Contact Form inquiry: ' + data.firstname + ' ' + data.lastname,
                Charset: 'UTF-8'
            }
        },
        Source: SENDER
    }
    ses.sendEmail(params, done);
}
